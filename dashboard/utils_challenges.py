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


# --- GAMIFICATION LOGIC ---
from .models import GamificationProfile, DailyQuest

def check_daily_streak(user):
    """
    Checks if the user missed a day. If so, resets streak.
    Should be called on dashboard load.
    """
    try:
        profile = user.gamification_profile
        today = timezone.localdate()
        
        if profile.last_streak_update:
            delta = (today - profile.last_streak_update).days
            # If delta is 1, they last completed yesterday (Safe).
            # If delta is 0, they last completed today (Safe).
            # If delta > 1, they missed a day (Reset).
            if delta > 1:
                profile.current_streak = 0
                profile.save()
    except Exception:
        pass

def update_quest_status(user):
    """
    Updates status for ACTIVE challenges.
    - Checks if FAILED (e.g. spent money in No-Spend challenge).
    - Updates Progress (Days passed without failure).
    - Completes if Duration met.
    """
    quests = DailyQuest.objects.filter(user=user, status='ACTIVE')
    profile, _ = GamificationProfile.objects.get_or_create(user=user)
    today = timezone.localdate()
    
    for quest in quests:
        # 1. Check for FAILURE Check
        # For No-Spend, if ANY transaction exists in forbidden category since start_date, it flows to FAILED.
        if 'NO_SPEND' in quest.quest_type:
            target_cat = quest.target_variable.get('target_category')
            # Check all txns from start_date (precise time) to now
            bad_txns = Transaction.objects.filter(
                user=user, 
                date__gte=quest.start_date, # PRECISE TIMESTAMP CHECK
                category__iexact=target_cat
            )
            
            if bad_txns.exists():
                quest.status = 'FAILED'
                quest.save()
                continue
        
        # 2. Update Progress (Time-based or Accumulation)
        if quest.quest_type in ['NO_SPEND_CATEGORY', 'NO_SPEND_VENDOR', 'STREAK_KEEPER']:
            # Progress = Days elapsed since start
            # Convert start_date (datetime) to date for subtraction
            start_local_date = timezone.localdate(quest.start_date)
            days_elapsed = (today - start_local_date).days
            quest.current_progress = max(0, days_elapsed)
            
            # Check Completion
            if days_elapsed >= quest.duration_days:
                quest.status = 'COMPLETED'
                # Award
                profile.points += quest.reward_points
                profile.total_xp += quest.reward_xp
                # Update Level
                profile.level = 1 + (profile.total_xp // 1000)
                profile.save()
            
            quest.save()

        elif quest.quest_type == 'SAVE_AMOUNT':
            # Accumulate savings since start
            saved_so_far = Transaction.objects.filter(
                user=user,
                date__gte=quest.start_date, # PRECISE TIMESTAMP CHECK
                category__in=['Savings', 'Investment']
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            # Here progress depends on Amount, not Days? 
            # Or is it "Save X per day"? 
            # The current AI prompt says "Save X amount". 
            # Let's treat progress as % of amount for the bar?
            # But the model field `current_progress` is Integer (Days).
            # This is a mismatch. Let's hack it: 
            # For SAVE, `current_progress` stores the % (0-100) temporarily or we stick to duration?
            # If the challenge is "Save 500 in 3 days", we check if 500 is met within 3 days.
            target = quest.target_variable.get('amount', 0)
            if saved_so_far >= target:
                quest.status = 'COMPLETED'
                profile.points += quest.reward_points
                profile.total_xp += quest.reward_xp
                profile.level = 1 + (profile.total_xp // 1000)
                profile.save()
            elif (today - timezone.localdate(quest.start_date)).days >= quest.duration_days:
                # Time run out without hitting target
                quest.status = 'FAILED'
            
            quest.save()
