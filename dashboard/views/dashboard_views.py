from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from dashboard.models import Transaction
from django.utils import timezone
from datetime import timedelta


@login_required
def home(request):
    user = request.user
    
    # Current Stats
    try:
        initial_balance = user.profile.cash_balance
    except:
        initial_balance = 0

    income = Transaction.objects.filter(user=user, transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
    expense = Transaction.objects.filter(user=user, transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = initial_balance + income - expense
    
    # Previous Month Stats (30 days ago)
    last_month = timezone.now() - timedelta(days=30)
    income_last = Transaction.objects.filter(user=user, date__lt=last_month, transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
    expense_last = Transaction.objects.filter(user=user, date__lt=last_month, transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
    balance_last = initial_balance + income_last - expense_last
    
    # Calculate Percentage Change
    if balance_last != 0:
        percentage_change = ((balance - balance_last) / abs(balance_last)) * 100
    else:
        percentage_change = 0 # If start was 0 and now is 0, no change. If start 0 and now >0, technically infinite growth.
        if balance > 0:
            percentage_change = 100
        elif balance < 0:
            percentage_change = -100

    recent_transactions = Transaction.objects.filter(user=user).order_by('-date')[:5]
    
    context = {
        'total_balance': balance,
        'total_income': income,
        'total_expense': expense,
        'recent_transactions': recent_transactions,
        'percentage_change': percentage_change,
        'balance_is_positive': percentage_change >= 0
    }
    return render(request, 'dashboard/home.html', context)

