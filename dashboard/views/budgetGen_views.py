from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
import calendar
from dashboard.models import Transaction

# --- HELPER: Get Data for Calculations ---
def get_monthly_data(user):
    now = timezone.now()
    
    # 1. Get Income (Sum of INCOME transactions for current month)
    income_agg = Transaction.objects.filter(
        user=user,
        transaction_type='INCOME',
        date__month=now.month,
        date__year=now.year
    ).aggregate(Sum('amount'))
    
    # Handle case where result is None (no income yet)
    income = income_agg['amount__sum'] or Decimal(0)
    
    # 2. Get Actual Expenses for Current Month
    expenses = Transaction.objects.filter(
        user=user,
        transaction_type='EXPENSE',
        date__month=now.month,
        date__year=now.year
    )
    
    # Group Expenses by "Needs" and "Wants"
    needs_categories = ['FOOD', 'BILLS', 'TRANSPORT', 'EDUCATION', 'HEALTH']
    
    spent_needs = expenses.filter(category__in=needs_categories).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    spent_wants = expenses.exclude(category__in=needs_categories).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    
    return income, spent_needs, spent_wants

# --- HELPER: Strategy Logics ---

def calculate_50_30_20(income):
    """Classic: 50% Needs, 30% Wants, 20% Savings"""
    return {
        'name': 'Classic Rule (50/30/20)',
        'needs_budget': income * Decimal('0.50'),
        'wants_budget': income * Decimal('0.30'),
        'savings_budget': income * Decimal('0.20'),
        'description': 'Best for balanced financial health.'
    }

def calculate_70_20_10(income):
    """Survivor: 70% Needs, 10% Wants, 20% Savings/Debt"""
    return {
        'name': 'Survivor Rule (70/20/10)',
        'needs_budget': income * Decimal('0.70'),
        'wants_budget': income * Decimal('0.10'),
        'savings_budget': income * Decimal('0.20'),
        'description': 'Best for high rent or tight income months.'
    }

def calculate_savings_first(income):
    """Savings First: Lock 30% for Savings, split the rest"""
    # 30% Savings, 45% Needs, 25% Wants
    return {
        'name': 'Aggressive Saver (Savings First)',
        'needs_budget': income * Decimal('0.45'),
        'wants_budget': income * Decimal('0.25'),
        'savings_budget': income * Decimal('0.30'),
        'description': 'Best if you have a big goal (Car/House) coming up.'
    }

# --- MAIN VIEW ---
@login_required
def budget_generator_view(request):
    user = request.user
    income, spent_needs, spent_wants = get_monthly_data(user)
    
    # 1. Check if user manually selected a strategy
    selected_strategy = request.GET.get('strategy') # e.g. 'survivor', 'savings'
    
    # Default variables
    strategy = {}
    recommendation_reason = ""

    # 2. Logic: Manual Override vs AI Auto-Detect
    if selected_strategy == 'classic':
        strategy = calculate_50_30_20(income)
        recommendation_reason = "You selected the Classic 50/30/20 Rule."
        
    elif selected_strategy == 'survivor':
        strategy = calculate_70_20_10(income)
        recommendation_reason = "You selected the Survivor Rule (High Essentials)."
        
    elif selected_strategy == 'savings':
        strategy = calculate_savings_first(income)
        recommendation_reason = "You selected the Aggressive Saver Plan."
        
    else:
        # --- AI AUTO-DETECTION ---
        # Safeguard: If income is 0, default to Classic to avoid DivisionByZero error
        if income == 0:
            strategy = calculate_50_30_20(income)
            recommendation_reason = "Add Income transactions to see AI suggestions."
            selected_strategy = 'classic'
        
        elif (spent_needs / income) > Decimal('0.55'):
            strategy = calculate_70_20_10(income)
            recommendation_reason = "AI Suggestion: Your essentials are high (>55%), so we switched to Survivor Mode."
            selected_strategy = 'survivor' 
            
        elif (spent_needs / income) < Decimal('0.35'):
            strategy = calculate_savings_first(income)
            recommendation_reason = "AI Suggestion: Low expenses detected! You can save aggressively."
            selected_strategy = 'savings'
            
        else:
            strategy = calculate_50_30_20(income)
            recommendation_reason = "AI Suggestion: Your spending is balanced. Classic mode is best."
            selected_strategy = 'classic'

    # 3. Calculate "Daily Safe Spend"
    now = timezone.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_left = days_in_month - now.day
    days_left = max(1, days_left) # Prevent division by zero
    
    wants_remaining = strategy['wants_budget'] - spent_wants
    daily_safe_spend = max(0, wants_remaining / days_left)

    # 4. Prepare Context
    context = {
        'strategy': strategy,
        'income': income,
        'current_selection': selected_strategy,
        'recommendation_reason': recommendation_reason,
        
        # Actuals
        'spent_needs': spent_needs,
        'spent_wants': spent_wants,
        'spent_total': spent_needs + spent_wants,
        
        # Variances (Budget - Actual)
        'left_needs': strategy['needs_budget'] - spent_needs,
        'left_wants': wants_remaining,
        
        # Extras
        'daily_safe_spend': daily_safe_spend,
        'days_left': days_left,
    }
    
    return render(request, 'dashboard/budget_generator.html', context)