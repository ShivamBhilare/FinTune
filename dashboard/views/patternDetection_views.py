from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from dashboard.models import Transaction
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth, ExtractWeekDay, TruncDay
import json
from django.utils import timezone
from datetime import timedelta
from dashboard.utils import get_recurring_stats, get_most_active_day, get_financial_persona

@login_required
def pattern_detection(request):
    user = request.user
    
    # 1. Recurring Transactions
    recurring_list, total_recurring_monthly = get_recurring_stats(user)

    # 2. Identify High Spending Categories (Top 3) for list
    high_spending_categories = (
        Transaction.objects.filter(user=user, transaction_type='EXPENSE')
        .values('category')
        .annotate(total_amount=Sum('amount'))
        .order_by('-total_amount')[:3]
    )

    # 3. Prepare Data for Charts
    
    # Category Distribution (All Categories)
    cat_distribution = (
        Transaction.objects.filter(user=user, transaction_type='EXPENSE')
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    
    cat_labels = [item['category'] for item in cat_distribution]
    cat_data = [float(item['total']) for item in cat_distribution]

    # Daily Spending Trend (Last 30 Days)
    last_30_days = timezone.now() - timedelta(days=30)
    daily_trend = (
        Transaction.objects.filter(user=user, transaction_type='EXPENSE', date__gte=last_30_days)
        .annotate(day=TruncDay('date'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )
    
    trend_labels = [item['day'].strftime('%b %d') for item in daily_trend]
    trend_data = [float(item['total']) for item in daily_trend]

    # 4. Advanced Insights (Persona & Active Day)
    most_active_day = get_most_active_day(user)
    persona_data = get_financial_persona(user)

    context = {
        'recurring_transactions': recurring_list,
        'high_spending_categories': high_spending_categories,
        'cat_labels': cat_labels,
        'cat_data': cat_data,
        'trend_labels': trend_labels,
        'trend_data': trend_data,
        'most_active_day': most_active_day,
        'persona': persona_data['persona'],
        'persona_desc': persona_data['persona_desc'],
        'persona_icon': persona_data['icon'],
        'total_recurring_monthly': total_recurring_monthly
    }
    
    return render(request, 'dashboard/pattern_detection.html', context)
