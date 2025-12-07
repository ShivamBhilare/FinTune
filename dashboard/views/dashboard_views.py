from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from dashboard.models import Transaction
from django.utils import timezone
from datetime import timedelta
from .healthScore_views import get_health_score_context


from dashboard.utils import get_financial_persona, get_most_active_day, get_recurring_stats

@login_required
def home(request):
    user = request.user
    
    # Current Stats
    try:
        # Handling the case where Profile might not exist or cash_balance is accessed
        initial_balance = 0
        if hasattr(user, 'profile'):
             initial_balance = user.profile.cash_balance or 0
    except:
        initial_balance = 0

    income = Transaction.objects.filter(user=user, transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
    expense = Transaction.objects.filter(user=user, transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = initial_balance + income - expense

    # Calculate Current Month Expense for Display
    now = timezone.now()
    current_month_expense = Transaction.objects.filter(
        user=user, 
        transaction_type='EXPENSE', 
        date__month=now.month, 
        date__year=now.year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Previous Month Stats (30 days ago)
    last_month = now - timedelta(days=30)
    income_last = Transaction.objects.filter(user=user, date__lt=last_month, transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
    expense_last = Transaction.objects.filter(user=user, date__lt=last_month, transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
    balance_last = initial_balance + income_last - expense_last
    
    # Calculate Percentage Change
    if balance_last != 0:
        percentage_change = ((balance - balance_last) / abs(balance_last)) * 100
    else:
        percentage_change = 0 
        if balance > 0:
            percentage_change = 100
        elif balance < 0:
            percentage_change = -100

    recent_transactions = Transaction.objects.filter(user=user).order_by('-date')[:5]
    
    # Pattern Detection Data
    persona_data = get_financial_persona(user)
    most_active_day = get_most_active_day(user)
    _, total_recurring = get_recurring_stats(user)

    context = {
        'total_balance': balance,
        'total_income': income,
        'total_expense': current_month_expense, # Using current month expense as requested
        'recent_transactions': recent_transactions,
        'percentage_change': percentage_change,
        'balance_is_positive': percentage_change >= 0,
        'persona': persona_data['persona'],
        'persona_desc': persona_data['persona_desc'],
        'persona_icon': persona_data['icon'],
        'most_active_day': most_active_day,
        'total_recurring': total_recurring
    }
    
    # Add Health Score Context
    try:
        health_context = get_health_score_context(user)
        context.update(health_context)
    except Exception as e:
        print(f"Error calculating health score: {e}")
        context.update({
            'health_score': 0,
            'message': "Set up profile to see score",
            'score_color': "text-slate-400",
            'progress_color': "bg-slate-700"
        })

    return render(request, 'dashboard/home.html', context)
