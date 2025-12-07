from dashboard.models import Transaction
from django.db.models import Count, Sum
from django.db.models.functions import ExtractWeekDay

import difflib

def are_similar(name1, name2):
    """
    Checks if two vendor names are similar using fuzzy matching.
    """
    n1 = name1.lower()
    n2 = name2.lower()
    
    # Simple clean: remove non-alphanumeric (except spaces)
    n1_clean = ''.join(c for c in n1 if c.isalnum() or c.isspace())
    n2_clean = ''.join(c for c in n2 if c.isalnum() or c.isspace())
    
    if n1_clean == n2_clean and n1_clean != "":
        return True

    ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
    return ratio > 0.80

def get_recurring_stats(user):
    """
    Identifies recurring transactions and calculates total monthly recurring cost.
    Uses fuzzy matching to group similar vendor names (e.g., 'D*mart' and 'Dmart').
    Returns a tuple: (recurring_list, total_recurring_monthly)
    """
    # 1. Fetch all candidate transactions
    transactions = (
        Transaction.objects.filter(user=user, transaction_type='EXPENSE')
        .exclude(category='Tax')
        .values('vendor_name', 'amount', 'date', 'description')
        .order_by('date')
    )
    
    # 2. Group by Amount first (optimization)
    amount_groups = {}
    for tx in transactions:
        amt = tx['amount']
        if amt not in amount_groups:
            amount_groups[amt] = []
        amount_groups[amt].append(tx)
        
    recurring_list = []
    total_recurring_monthly = 0
    
    # 3. Fuzzy match within amount groups
    for amt, tx_list in amount_groups.items():
        processed_indices = set()
        
        for i in range(len(tx_list)):
            if i in processed_indices:
                continue
                
            current = tx_list[i]
            group = [current]
            processed_indices.add(i)
            
            for j in range(i + 1, len(tx_list)):
                if j in processed_indices:
                    continue
                    
                other = tx_list[j]
                if are_similar(current['vendor_name'], other['vendor_name']):
                    group.append(other)
                    processed_indices.add(j)
            
            # If group has more than 1 item, it's recurring
            if len(group) > 1:
                # Use the most recent vendor name for display
                latest_tx = max(group, key=lambda x: x['date'])
                vendor_display = latest_tx['vendor_name']
                description_display = latest_tx['description']
                count = len(group)
                
                recurring_list.append({
                    'vendor': vendor_display,
                    'description': description_display,
                    'amount': amt,
                    'count': count,
                    'last_date': latest_tx['date'],
                    'total_spent': amt * count
                })
                total_recurring_monthly += amt

    # Sort by count descending
    recurring_list.sort(key=lambda x: x['count'], reverse=True)
        
    return recurring_list, total_recurring_monthly

def get_most_active_day(user):
    """
    Determines the day of the week with the most transactions.
    """
    active_day_data = (
        Transaction.objects.filter(user=user)
        .annotate(day=ExtractWeekDay('date'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('-count')
        .first()
    )
    
    day_map = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday', 5: 'Thursday', 6: 'Friday', 7: 'Saturday'}
    return day_map.get(active_day_data['day'], 'Unknown') if active_day_data else 'N/A'

def get_financial_persona(user):
    """
    Determines financial persona based on top spending category.
    Returns a dictionary with persona, desc, and icon.
    """
    # Category Distribution (All Categories)
    cat_distribution = (
        Transaction.objects.filter(user=user, transaction_type='EXPENSE')
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    
    persona = "The Balanced Spender"
    persona_desc = "You maintain a healthy mix of spending habits."
    icon = "fa-scale-balanced"
    
    if cat_distribution:
        top_cat = cat_distribution[0]['category']
        if top_cat == 'Food' or top_cat == 'Groceries':
            persona = "The Foodie"
            persona_desc = "Your heart (and wallet) belongs to good food!"
            icon = "fa-utensils"
        elif top_cat == 'Entertainment':
            persona = "The Fun Seeker"
            persona_desc = "You know how to enjoy life to the fullest."
            icon = "fa-gamepad"
        elif top_cat == 'Transportation':
            persona = "The Traveler"
            persona_desc = "Always on the move, exploring new places."
            icon = "fa-plane"
        elif top_cat == 'Clothing & Apparel':
            persona = "The Trendsetter"
            persona_desc = "Fashion is your passion, and it shows."
            icon = "fa-shirt"
        elif top_cat == 'Utilities' or top_cat == 'Housing':
            persona = "The Homebody"
            persona_desc = "You prioritize comfort and stability at home."
            icon = "fa-house"
        elif top_cat == 'Healthcare':
            persona = "The Wellness Guru"
            persona_desc = "Health is wealth, and you invest in it."
            icon = "fa-heart-pulse"
            
    return {
        'persona': persona,
        'persona_desc': persona_desc,
        'icon': icon
    }
