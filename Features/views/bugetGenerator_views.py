from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Case, When, Value, DecimalField
from django.utils import timezone
from decimal import Decimal
import calendar
from ..models import Transaction
from auth_user.models import UserProfile

def calculate_monthly_totals(user):
    """
    Helper function to calculate current month's financial totals.
    Returns a dictionary with Income, Needs, Wants, and Savings.
    """
    now = timezone.now()
    # Get first and last day of current month
    _, last_day = calendar.monthrange(now.year, now.month)
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    
    # 1. Calculate Total Income
    # Start with fixed monthly income from Profile
    try:
        profile_income = user.profile.monthly_income or Decimal('0.00')
    except UserProfile.DoesNotExist:
        profile_income = Decimal('0.00')
        
    # Add variable income from Transactions this month
    variable_income = Transaction.objects.filter(
        user=user,
        transaction_type='INCOME',
        date__range=(start_date, end_date)
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_income = profile_income + variable_income

    # 2. Get All Outflows (Expenses + Investments) for this month
    # We fetch EVERYTHING here, and then split them into Needs/Wants/Savings below.
    expenses = Transaction.objects.filter(
        user=user,
        transaction_type__in=['EXPENSE', 'INVESTMENT'],
        date__range=(start_date, end_date)
    )

    # Define Categories
    # Note: 'SIP', 'Stocks', 'Savings' are not in standard choices but handled if present
    needs_categories = [
        'Housing', 'Utilities', 'Healthcare', 'Transportation', 
        'Groceries', 'Tax', 'Food' 
    ]
    savings_categories = ['SIP', 'Stocks', 'Savings','Investment','Mutual Funds']
    
    # Calculate Buckets
    needs_total = expenses.filter(category__in=needs_categories).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    savings_total = expenses.filter(category__in=savings_categories).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Wants are everything else (Expense type - needs - savings)
    # We calculate explicitly to be safe, excluding the known needs/savings categories
    wants_total = expenses.exclude(
        category__in=needs_categories + savings_categories
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    return {
        'income': total_income,
        'needs': needs_total,
        'wants': wants_total,
        'savings': savings_total,
        'days_in_month': last_day,
        'remaining_days': last_day - now.day
    }

@login_required
def budget_generator_view(request):
    """
    Main view for the Budget Generator.
    Auto-suggests strategies and calculates daily safe spend.
    """
    totals = calculate_monthly_totals(request.user)
    
    income = totals['income']
    needs_spent = totals['needs']
    wants_spent = totals['wants']
    savings_spent = totals['savings']
    
    # Avoid division by zero
    if income > 0:
        needs_pct = (needs_spent / income) * 100
    else:
        needs_pct = Decimal('0.00')

    # Recommendation Logic
    recommendation = {
        'strategy': 'Classic',
        'reason': "Your needs are balanced (35-55% of income). The 50/30/20 rule is ideal.",
        'color': 'indigo'
    }
    
    if needs_pct > 55:
        recommendation = {
            'strategy': 'Survivor',
            'reason': f"Your needs are high ({needs_pct:.1f}%). Focus on essentials with 70/20/10.",
            'color': 'orange'
        }
    elif needs_pct < 35 and income > 0:
        recommendation = {
            'strategy': 'Aggressive',
            'reason': f"Your needs are low ({needs_pct:.1f}%). You can save more with 45/25/30.",
            'color': 'emerald'
        }

    # ... (Recommendation Logic remains the same)

    # Strategy Definitions (Needs, Wants, Savings)
    strategies = {
        'Classic': {'needs': 0.50, 'wants': 0.30, 'savings': 0.20},
        'Survivor': {'needs': 0.70, 'wants': 0.20, 'savings': 0.10},
        'Aggressive': {'needs': 0.45, 'wants': 0.25, 'savings': 0.30}
    }
    
    # 1. Determine which strategy to USE for calculations
    # Default to recommendation
    selected_strategy_name = recommendation['strategy']
    
    # Override if user explicitly requested one via GET param
    user_selection = request.GET.get('strategy')
    if user_selection in strategies:
        selected_strategy_name = user_selection

    strat_rules = strategies[selected_strategy_name]
    
    budget_allocations = {
        'needs_limit': income * Decimal(str(strat_rules['needs'])),
        'wants_limit': income * Decimal(str(strat_rules['wants'])),
        'savings_target': income * Decimal(str(strat_rules['savings'])),
    }
    
    # Calculate Remaining
    remaining = {
        'needs': budget_allocations['needs_limit'] - needs_spent,
        'wants': budget_allocations['wants_limit'] - wants_spent,
        'savings_to_go': budget_allocations['savings_target'] - savings_spent
    }
    
    # Daily Safe Spend
    # Logic: (Remaining Wants Budget) / Days Left
    dates_left = totals['remaining_days']
    if dates_left > 0 and remaining['wants'] > 0:
        daily_safe_spend = remaining['wants'] / dates_left
    else:
        daily_safe_spend = Decimal('0.00')

    context = {
        'totals': totals,
        'recommendation': recommendation,
        'allocations': budget_allocations,
        'remaining': remaining,
        'daily_safe_spend': daily_safe_spend,
        
        # Pass all strategies for frontend
        'strategies': strategies,
        'current_strategy': selected_strategy_name
    }

    return render(request, 'dashboard/budget_generator.html', context)
