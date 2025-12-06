from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from dashboard.models import Transaction

def get_health_score_context(user):
    now = timezone.now()

    # --- 1. Get User Income for CURRENT MONTH to simulate "Monthly Income" ---
    # Since we don't have a Profile model with a fixed salary, we sum actual income.
    monthly_income = Transaction.objects.filter(
        user=user,
        transaction_type='INCOME',
        date__month=now.month,
        date__year=now.year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

    
    # Filter: Current User + Expense Type + Current Month + Current Year
    current_month_expenses = Transaction.objects.filter(
        user=user,
        transaction_type='EXPENSE',
        date__month=now.month,
        date__year=now.year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

    # --- 3. The Health Score Logic (0-100) ---
    health_score = 0
    
    if monthly_income > 0:
        # Metric A: Savings Rate (Target: Save 20% of income)
        savings = monthly_income - current_month_expenses
        savings_rate = (savings / monthly_income) * 100
        
        # Scoring Rules for Savings
        if savings_rate >= 20:
            score_savings = 50  # Perfect score
        elif savings_rate < 0:
            score_savings = 0   # In Debt
        else:
            score_savings = (savings_rate / 20) * 50 # Scaled score

        # Metric B: Expense Control (Target: Spend < 80% of income)
        spend_ratio = (current_month_expenses / monthly_income) * 100
        
        if spend_ratio > 100:
            score_control = 0
        elif spend_ratio < 50:
            score_control = 50
        else:
            # If you spend 80%, you get 20pts. If you spend 50%, you get 50pts.
            score_control = 50 - (spend_ratio - 50)
            
        health_score = int(score_savings + max(0, score_control))
        
        # Clamp score between 0 and 100
        health_score = max(0, min(100, health_score))

    # --- 4. Determine UI Colors & Messages ---
    if health_score >= 80:
        score_color = "text-emerald-400" # Green
        progress_color = "bg-emerald-500"
        message = "Excellent! You're a master."
    elif health_score >= 50:
        score_color = "text-yellow-400" # Yellow
        progress_color = "bg-yellow-500"
        message = "Good, but watch your spending."
    else:
        score_color = "text-red-400" # Red
        progress_color = "bg-red-500"
        message = "Critical! Immediate action needed."

    return {
        'health_score': health_score,
        'score_color': score_color,     # For text
        'progress_color': progress_color, # For progress bar
        'message': message,
        'monthly_income': monthly_income,
        'current_expenses': current_month_expenses,
        'savings': monthly_income - current_month_expenses
    }