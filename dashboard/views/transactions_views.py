from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from dashboard.models import Transaction

@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    return render(request, 'dashboard/transaction_history.html', {'transactions': transactions})