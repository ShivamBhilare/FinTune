from .models import Transaction
from django.utils import timezone
from django.db.models import Sum

def get_challenge_progress(user, challenge_type, target_category=None, target_amount=None, target_time=None, start_time=None):
    """
    Returns a dict with progress info:
    {
        'current': float,
        'target': float,
        'percentage': int (0-100),
        'is_completed': bool
    }
    """
    txns = Transaction.objects.filter(user=user)
    
    if start_time:
         txns = txns.filter(date__gte=start_time)
    else:
         today_local = timezone.localdate()
         txns = txns.filter(date__date=today_local)

    current_val = 0
    target_val = target_amount or 0
    is_completed = False
    
    if challenge_type == 'SAVE_AMOUNT':
        current_val = txns.filter(category__in=['Savings', 'Investment']).aggregate(Sum('amount'))['amount__sum'] or 0
        if current_val >= target_val: is_completed = True
        
    elif challenge_type == 'TRANSACTION_BEFORE':
        # Result is binary. Either you did it or not.
        target_val = 1
        if target_time is not None:
            for txn in txns:
                if txn.date.hour < target_time:
                    current_val = 1
                    is_completed = True
                    break
                    
    elif challenge_type == 'NO_SPEND':
        # "Progress" is tricky here. 
        # Maybe "Hours survived"? Or just 0/1 (Failed/Success).
        # Let's say: 1 = Success, 0 = Failed (Spent).
        # CAUTION: verify logic previously returned "True" if NO spend data found.
        target_val = 1
        if target_category:
             exists = txns.filter(category__iexact=target_category).exists()
             if not exists:
                 current_val = 1
                 is_completed = True
             else:
                 current_val = 0
                 is_completed = False
    
    elif challenge_type == 'SPEND_LESS_THAN':
         # Target is Limit. 
         # Progress shows "Spent so far".
         # percentage = (Spent / Limit) * 100.
         # Completed if Spent < Limit.
         current_val = txns.filter(category__iexact=target_category).aggregate(Sum('amount'))['amount__sum'] or 0
         if current_val < target_val: is_completed = True
         
    # Calculate Percentage cap at 100
    if target_val > 0:
        pct = min(100, int((current_val / target_val) * 100))
    else:
        pct = 100 if is_completed else 0

    return {
        'current': current_val,
        'target': target_val,
        'percentage': pct,
        'is_completed': is_completed
    }

def verify_challenge(user, challenge_type, target_category=None, target_amount=None, target_time=None, start_time=None):
    """
    Verifies if the user has met the conditions for a challenge.
    start_time: DateTime when the challenge was accepted.
    """
    progress = get_challenge_progress(user, challenge_type, target_category, target_amount, target_time, start_time)
    return progress['is_completed']
