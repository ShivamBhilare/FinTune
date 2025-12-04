from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from dashboard.models import Transaction

@login_required
def home(request):
    user = request.user
    
    # Calculate totals
    income = Transaction.objects.filter(user=user, transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
    expense = Transaction.objects.filter(user=user, transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = income - expense
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=user).order_by('-date')[:5]
    
    context = {
        'total_balance': balance,
        'total_income': income,
        'total_expense': expense,
        'recent_transactions': recent_transactions
    }
    
    return render(request, 'dashboard/home.html', context)
