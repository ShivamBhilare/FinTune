from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..forms import ProfileForm

@login_required
def profile_view(request):
    """
    Profile management view.
    Allows users to view and update their profile information.
    Syncs 'Current Balance' display with Dashboard 'Total Balance'.
    """
    user = request.user
    
    def get_net_delta(monthly_income):
        # Helper to get net flow excluding initial balance
        def get_sum(tx_type):
            return Transaction.objects.filter(user=user, transaction_type=tx_type, is_external=False).aggregate(Sum('amount'))['amount__sum'] or 0
        
        income = get_sum('INCOME') + (monthly_income or 0)
        expense = get_sum('EXPENSE')
        investment = get_sum('INVESTMENT')
        return income - (expense + investment)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            # Get the total balance the user WANTS to see
            submitted_balance = form.cleaned_data.get('cash_balance', 0) or 0
            submitted_income = form.cleaned_data.get('monthly_income', 0) or 0
            
            # Calculate back the necessary initial balance
            net_delta = get_net_delta(submitted_income)
            new_initial_balance = submitted_balance - net_delta
            
            profile = form.save(commit=False)
            profile.cash_balance = new_initial_balance
            profile.save()
            profile.user.save() # Save user fields (first/last name)
            
            # Re-init form with the calculated total for display
            form = ProfileForm(instance=request.user.profile)
            form.fields['cash_balance'].initial = submitted_balance
            
            return render(request, 'dashboard/profile.html', {'form': form, 'success': True})
    else:
        form = ProfileForm(instance=request.user.profile)
        # Pre-populate form with the Calculated Total Balance
        current_profile_income = user.profile.monthly_income
        net_delta = get_net_delta(current_profile_income)
        calculated_balance = (user.profile.cash_balance or 0) + net_delta
        form.fields['cash_balance'].initial = calculated_balance
    
    return render(request, 'dashboard/profile.html', {'form': form})

from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from ..models import Transaction
from .health_score import get_health_score_context

@login_required
def dashboard_view(request):
    """
    Main dashboard view.
    Redirects here after login.
    """
    user = request.user
    
    # Current Stats
    try:
        initial_balance = 0
        if hasattr(user, 'profile'):
            initial_balance = user.profile.cash_balance or 0
    except:
        initial_balance = 0

    # Helper to get sum of transactions
    def get_transaction_sum(queryset, tx_type):
        return queryset.filter(transaction_type=tx_type, is_external=False).aggregate(Sum('amount'))['amount__sum'] or 0

    # Init income from profile
    try:
        profile_income = user.profile.monthly_income or 0
    except:
        profile_income = 0
            
    # Current totals
    income = get_transaction_sum(Transaction.objects.filter(user=user), 'INCOME') + profile_income
    expense = get_transaction_sum(Transaction.objects.filter(user=user), 'EXPENSE')
    investment = get_transaction_sum(Transaction.objects.filter(user=user), 'INVESTMENT')
    
    balance = initial_balance + income - (expense + investment)

    # Calculate Current Month Expense for Display
    now = timezone.now()
    current_month_expense = Transaction.objects.filter(
        user=user, 
        transaction_type='EXPENSE', 
        is_external=False,
        date__month=now.month, 
        date__year=now.year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Previous Month Stats (30 days ago reference point for trend)
    last_month = now - timedelta(days=30)
    base_qs_last = Transaction.objects.filter(user=user, date__lt=last_month)
    
    income_last = get_transaction_sum(base_qs_last, 'INCOME')
    expense_last = get_transaction_sum(base_qs_last, 'EXPENSE')
    investment_last = get_transaction_sum(base_qs_last, 'INVESTMENT')
    
    balance_last = initial_balance + income_last - (expense_last + investment_last)
    
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
    
    # Get Health Score Context
    context = get_health_score_context(user)
    
    # Update context with dashboard stats
    context.update({
        'total_balance': balance,
        'total_income': income,
        'total_expense': current_month_expense, 
        'recent_transactions': recent_transactions,
        'percentage_change': round(percentage_change, 1),
        'balance_is_positive': percentage_change >= 0
    })

    return render(request, 'dashboard/home.html', context)

@login_required
def questionnaire_view(request):
    """
    Questionnaire view.
    Redirects here if LOGIN_REDIRECT_URL is set to 'questionnaire'.
    """
    return render(request, 'account/questionnaire.html')

def home_redirect_view(request):
    """
    Root URL view.
    Redirects to questionnaire if logged in, else to login page.
    """
    from django.shortcuts import redirect
    if request.user.is_authenticated:
        return redirect('questionnaire')
    return redirect('account_login')
