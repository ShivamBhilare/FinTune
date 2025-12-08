from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from dashboard.models import Transaction

def get_health_score_context(user):
    now = timezone.now()
    
    # 1. Income (Fixed Profile Income + Variable Income Transactions)
    try:
        fixed_income = user.profile.monthly_income or Decimal(0)
    except Exception:
        fixed_income = Decimal(0)

    # Fetch variable income (e.g., side hustles, gifts) from transactions
    variable_income = Transaction.objects.filter(
        user=user,
        transaction_type='INCOME',
        date__month=now.month,
        date__year=now.year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

    monthly_income = fixed_income + variable_income

    # 2. Expenses (Include ALL, even external)
    monthly_expenses = Transaction.objects.filter(
        user=user,
        transaction_type='EXPENSE',
        date__month=now.month,
        date__year=now.year,
        # is_external=False  <-- Commented out to include external expenses
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

    # 3. Investments (Include ALL, even external)
    monthly_investments = Transaction.objects.filter(
        user=user,
        transaction_type='INVESTMENT',
        date__month=now.month,
        date__year=now.year,
        # is_external=False  <-- Commented out to include external investments
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

    # --- ADVANCED HEALTH SCORE LOGIC (Total 100) ---
    health_score = 0
    
    if monthly_income > 0:
        # A. Burn Rate (40 Points): Expenses vs Income
        # Goal: Keep expenses low (e.g. < 50% is perfect)
        expense_ratio = (monthly_expenses / monthly_income) * 100
        if expense_ratio <= 50:
            score_expense = 40  # Perfect (Living well within means)
        elif expense_ratio >= 100:
            score_expense = 0   # Broke
        else:
            # Linear decay: 50% -> 40pts, 100% -> 0pts
            # Range is 50. Points range is 40. Scale factor = 40/50 = 0.8
            score_expense = 40 - ((expense_ratio - 50) * Decimal(0.8))

        # B. Investment Rate (40 Points): Building Wealth
        # Goal: Invest 20% of income
        invest_ratio = (monthly_investments / monthly_income) * 100
        if invest_ratio >= 20:
            score_invest = 40 # Perfect
        else:
            # Scale: 0% -> 0pts, 20% -> 40pts
            score_invest = (invest_ratio / 20) * 40

        # C. Cash Flow (20 Points): Positive Net Flow
        # Net Flow = Income - Expenses - Investments
        net_flow = monthly_income - monthly_expenses - monthly_investments
        if net_flow >= 0:
            score_cashflow = 20
        else:
            score_cashflow = 0 # Deficit spending

        health_score = int(score_expense + score_invest + score_cashflow)
        # Clamp to 100 max
        health_score = max(0, min(100, health_score))

    # --- UI Formatting ---
    if health_score >= 80:
        score_color = "text-emerald-400"
        progress_color = "bg-emerald-500"
        message = "Excellent! You're a Wealth Builder."
    elif health_score >= 50:
        score_color = "text-yellow-400"
        progress_color = "bg-yellow-500"
        message = "Good, but try to boost investments."
    else:
        score_color = "text-red-400"
        progress_color = "bg-red-500"
        message = "Critical! Your expenses are too high."

    return {
        'health_score': health_score,
        'score_color': score_color,
        'progress_color': progress_color,
        'message': message,
        'monthly_income': monthly_income,
        'current_expenses': monthly_expenses,
        'monthly_investments': monthly_investments
    }