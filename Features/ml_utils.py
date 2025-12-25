import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import Transaction
import difflib
import datetime

def predict_spending_arima(user):
    """
    Forecasts daily spending for the next 30 days using ARIMA.
    Returns a list of dictionaries: [{'date': 'YYYY-MM-DD', 'amount': float}, ...]
    """
    # 1. Fetch Spending Data (Expenses only)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=90) # Use last 90 days for better trend
    
    transactions = Transaction.objects.filter(
        user=user,
        transaction_type='EXPENSE',
        date__gte=start_date,
        date__lte=end_date
    ).values('date').annotate(total_amount=Sum('amount')).order_by('date')

    if not transactions:
        return []

    # 2. Prepare DataFrame
    df = pd.DataFrame(list(transactions))
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Fill missing days with 0
    idx = pd.date_range(start_date, end_date)
    df = df.reindex(idx, fill_value=0)
    
    data = df['total_amount']

    # 3. Fit Model (Smart Selection)
    # Check sparsity: if > 50% days are 0, ARIMA might be poor. Use Moving Average.
    non_zero_days = (df['total_amount'] > 0).sum()
    total_days = len(df)
    
    forecast_values = []
    
    if non_zero_days < (total_days * 0.1): # Less than 10% data
        # Fallback: Simple Average of non-zero days (or 0)
        avg_spend = df[df['total_amount'] > 0]['total_amount'].mean() if non_zero_days > 0 else 0
        # Create a flat forecast with slight noise for realism
        import random
        for _ in range(30):
            noise = random.uniform(0.9, 1.1)
            forecast_values.append(max(0, avg_spend * noise))
            
    else:
        try:
            # Fit ARIMA
            model = ARIMA(data, order=(5,1,0)) 
            model_fit = model.fit()
            forecast_values = model_fit.forecast(steps=30).tolist()
        except Exception:
            # Fallback if ARIMA fails: Exponential Moving Average
            forecast_values = data.ewm(span=30).mean().iloc[-1]
            forecast_values = [forecast_values] * 30

    # 4. Format Output
    forecast_data = []
    next_day = end_date + timedelta(days=1)
    
    for i, amount in enumerate(forecast_values):
        date_str = (next_day + timedelta(days=i)).strftime('%Y-%m-%d')
        safe_amount = max(0.0, float(amount))
        forecast_data.append({'date': date_str, 'amount': round(safe_amount, 2)})
        
    return forecast_data

def get_recurring_stats(user):
    """
    Identifies recurring transactions using fuzzy matching on vendor names.
    Returns: list of recurring items, total monthly recurring cost
    """
    # Get all expenses ordered by date desc
    transactions = Transaction.objects.filter(
        user=user,
        transaction_type='EXPENSE'
    ).exclude(category='Tax').order_by('-date')

    # Group by similarity
    # Structure: { 'canonical_name': { 'vendors': set(), 'amounts': [], 'dates': [], 'count': 0 } }
    groups = {}
    
    processed_ids = set()

    for tx in transactions:
        if tx.id in processed_ids:
            continue
            
        name = tx.vendor_name.strip() if tx.vendor_name else "Unknown"
        amount = float(tx.amount)
        
        # Try to find a match in existing groups
        match_found = False
        for key in groups:
            # Check 1: Fuzzy Name Match > 0.8
            ratio = difflib.SequenceMatcher(None, key.lower(), name.lower()).ratio()
            
            # Check 2: Exact Amount Match (Often key for subscriptions)
            # OR High Name Match (>0.9) if amount varies slightly
            amount_match = False
            if groups[key]['amounts']:
                 # Check if this amount matches the most common amount in group or just last one
                 if abs(groups[key]['amounts'][0] - amount) < 1.0: # Tolerance of 1.0
                     amount_match = True
            
            if (ratio > 0.8 and amount_match) or ratio > 0.95:
                # It's a match! add to group
                groups[key]['vendors'].add(name)
                groups[key]['amounts'].append(amount)
                groups[key]['dates'].append(tx.date)
                groups[key]['count'] += 1
                groups[key]['total_spent'] += amount
                if tx.date > groups[key]['last_date']:
                     groups[key]['last_date'] = tx.date
                match_found = True
                break
        
        if not match_found:
            groups[name] = {
                'vendors': {name},
                'amounts': [amount],
                'dates': [tx.date],
                'count': 1,
                'last_date': tx.date,
                'total_spent': amount
            }
        
    # Filter for "Recurring" (e.g., count >= 2 AND spread over time)
    recurring_list = []
    total_monthly_recurring = 0.0
    
    for name, data in groups.items():
        if data['count'] >= 2:
            # Simple heuristic: Identify as recurring
            avg_amount = sum(data['amounts']) / len(data['amounts'])
            
            recurring_list.append({
                'vendor': name,
                'amount': round(avg_amount, 2),
                'count': data['count'],
                'last_date': data['last_date'],
                'total_impact': round(data['total_spent'], 2)
            })
            
            # Estimate monthly: if last date is recent (< 35 days), add to monthly
            if (timezone.now().date() - data['last_date']).days < 35:
                total_monthly_recurring += avg_amount

    return recurring_list, round(total_monthly_recurring, 2)

def get_most_active_day(user):
    """
    Returns the day of the week with highest transaction volume.
    """
    from django.db.models.functions import ExtractWeekDay
    
    # 1=Sunday, 2=Monday, ..., 7=Saturday (Django default)
    # Note: Logic might vary by DB, but usually standard.
    qs = Transaction.objects.filter(user=user).annotate(
        weekday=ExtractWeekDay('date')
    ).values('weekday').annotate(
        count=Count('id')
    ).order_by('-count')
    
    if not qs:
        return "N/A"
        
    day_map = {
        1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday',
        5: 'Thursday', 6: 'Friday', 7: 'Saturday'
    }
    
    top_day_idx = qs[0]['weekday']
    return day_map.get(top_day_idx, "Unknown")

def get_financial_persona(user):
    """
    Determines financial persona based on top spending category.
    """
    # Get top category
    top_cat_qs = Transaction.objects.filter(
        user=user, 
        transaction_type='EXPENSE'
    ).values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    if not top_cat_qs:
        return {
            'persona': 'The Saver',
            'desc': 'You have minimal spending. Great job!',
            'icon': 'piggy-bank'
        }
        
    top_cat = top_cat_qs[0]['category']
    
    personas = {
        'Food': {'persona': 'The Foodie', 'desc': 'Good food is your good mood.', 'icon': 'utensils'},
        'Entertainment': {'persona': 'Fun Seeker', 'desc': 'You assume life is for living!', 'icon': 'party-popper'},
        'Transportation': {'persona': 'The Traveler', 'desc': 'Always on the move.', 'icon': 'plane'},
        'Clothing & Apparel': {'persona': 'Trendsetter', 'desc': 'Dressing to impress.', 'icon': 'shirt'},
        'Housing': {'persona': 'The Homebody', 'desc': 'Making your space a sanctuary.', 'icon': 'home'},
        'Utilities': {'persona': 'The Homebody', 'desc': 'Keeping the lights on and home cozy.', 'icon': 'home'},
        'Healthcare': {'persona': 'Wellness Guru', 'desc': 'Health is wealth.', 'icon': 'activity'},
        'Investment': {'persona': 'The Investor', 'desc': 'Building for the future.', 'icon': 'trending-up'},
        'Groceries': {'persona': 'Master Chef', 'desc': 'Cooking up storms at home.', 'icon': 'shopping-cart'},
    }
    
    return personas.get(top_cat, {
        'persona': 'Balanced Spender', 
        'desc': f'You assume spending on {top_cat} is important.', 
        'icon': 'wallet'
    })
