from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
import json
from ..models import Transaction
from ..ml_utils import (
    predict_spending_arima, 
    get_recurring_stats, 
    get_most_active_day, 
    get_financial_persona
)

@login_required
def pattern_detection_view(request):
    user = request.user
    
    # 1. Run ML & Rule-Based Logic
    forecast_data = predict_spending_arima(user)
    recurring_list, monthly_recurring_total = get_recurring_stats(user)
    persona_data = get_financial_persona(user)
    active_day = get_most_active_day(user)
    
    # 2. Daily Spending Trend (Last 30 Days) - for Chart
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    daily_spend_qs = Transaction.objects.filter(
        user=user, 
        transaction_type='EXPENSE',
        date__gte=start_date,
        date__lte=end_date
    ).values('date').annotate(total=Sum('amount')).order_by('date')
    
    # 2. Prepare Data for Charts
    
    # A. Category Data
    cat_dist_qs = Transaction.objects.filter(
        user=user, 
        transaction_type='EXPENSE'
    ).values('category').annotate(total=Sum('amount')).order_by('-total')
    
    category_data = {item['category']: float(item['total']) for item in cat_dist_qs}
    
    # B. Trend & Forecast Data
    # We want a single list of objects: { date: '...', amount: 123, is_forecast: bool }
    
    # Historical (Last 30 Days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    daily_spend_qs = Transaction.objects.filter(
        user=user, 
        transaction_type='EXPENSE',
        date__gte=start_date,
        date__lte=end_date
    ).values('date').annotate(total=Sum('amount')).order_by('date')
    
    history_map = {item['date']: float(item['total']) for item in daily_spend_qs}
    
    trend_and_forecast = []
    
    # Fill History (ensure no gaps)
    current = start_date
    while current <= end_date:
        trend_and_forecast.append({
            'date': current.strftime('%Y-%m-%d'),
            'amount': history_map.get(current, 0.0),
            'is_forecast': False
        })
        current += timedelta(days=1)
        
    # Append Forecast
    for item in forecast_data:
        trend_and_forecast.append({
            'date': item['date'],
            'amount': item['amount'],
            'is_forecast': True
        })
    
    context = {
        'persona': persona_data,
        'most_active_day': active_day,
        'recurring_total': monthly_recurring_total,
        'recurring_stats': recurring_list,
        'total_transactions': Transaction.objects.filter(user=user).count(),
        
        # JSON Data for JS
        'category_data': json.dumps(category_data),
        'trend_and_forecast': json.dumps(trend_and_forecast),
    }
    
    return render(request, 'dashboard/pattern_detection.html', context)
