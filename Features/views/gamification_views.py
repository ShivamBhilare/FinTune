import json
import logging
import google.generativeai as genai
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, Count
from django.db.models.functions import ExtractWeekDay

# --- Models ---
from ..models import GamificationProfile, DailyQuest, Transaction

# --- Internal Views/Utils ---
from .bugetGenerator_views import calculate_monthly_totals
from ..ml_utils import get_recurring_stats, get_most_active_day, get_financial_persona

logger = logging.getLogger(__name__)

# ==========================================
# CONSTANTS
# ==========================================

NEEDS_CATEGORIES = ['Housing', 'Utilities', 'Groceries', 'Healthcare', 'Tax']

# ==========================================
# HELPER FUNCTIONS (Adapting missing utils)
# ==========================================

def get_monthly_data(user):
    """
    Wrapper to adapt calculate_monthly_totals to the expected format.
    Returns: income, spent_needs, spent_wants, saved_savings
    """
    totals = calculate_monthly_totals(user)
    return totals['income'], totals['needs'], totals['wants'], totals['savings']

# ==========================================
# CHALLENGE PROGRESS & VERIFICATION LOGIC
# ==========================================

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
            # We need to check the time of transaction. 
            # Assuming 'date' is actually DateField, checking hour implies we might need created_at if available or assume checks are date based.
            # But Transaction model has 'date' as DateField usually, checking model: date = models.DateField(default=timezone.now)
            # However, created_at is DateTimeField. Use created_at for time check if date is just date.
            # But user logic passed 'start_time' for filtering.
            
            # Using created_at for time check logic
            for txn in txns:
                # Check hour using local time
                if txn.created_at and timezone.localtime(txn.created_at).hour < target_time:
                    current_val = 1
                    is_completed = True
                    break
                    
    elif challenge_type == 'NO_SPEND':
        # "Progress" is tricky here. 
        # Maybe "Hours survived"? Or just 0/1 (Failed/Success).
        # Let's say: 1 = Success, 0 = Failed (Spent).
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
                created_at__gte=quest.start_date, # PRECISE TIMESTAMP CHECK (Use created_at for time precision)
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

# ==========================================
# AI GENERATION LOGIC
# ==========================================

def generate_personalized_quests(user):
    """
    Generates 3 personalized quests using Privacy-First Context.
    Uses local pattern detection (Persona, Recurring, Budget) and sends only high-level info to Gemini.
    """
    try:
        # 1. Gather Local Context (Privacy-Safe)
        persona_data = get_financial_persona(user)
        persona_name = persona_data.get('persona', 'The Balanced Spender')
        
        recurring_list, total_recurring_amount = get_recurring_stats(user)
        recurring_count = len(recurring_list)
        
        most_active_day = get_most_active_day(user)
        
        # Budget Data
        # get_monthly_data returns: income, spent_needs, spent_wants, saved_savings
        try:
            income, spent_needs, spent_wants, saved_savings = get_monthly_data(user)
            # Calculate percentages for context
            needs_pct = int((spent_needs / income * 100)) if income > 0 else 0
            wants_pct = int((spent_wants / income * 100)) if income > 0 else 0
        except Exception:
            needs_pct = 50
            wants_pct = 30 # Default/Fallback

        # 2. Construct Privacy-Preserving Prompt (Variable Streak Challenge)
        prompt = f"""
        Role: Gamification Engine for FinTune.
        User Context:
        - Persona: "{persona_name}"
        - Top Spending Habit: Analyze {most_active_day} trends.
        - Recurring Bills: {recurring_count} identified.
        
        Task: Generate ONE Personalized Streak Challenge to break a spending habit.
        
        The goal is to challenge the user to STOP spending on their most problematic category or vendor for a set number of days.
        
        Rules:
        1. Look at their Persona/Habits. 
           - If "The Foodie", challenge: "No Outside Food for 5 Days" (Category: Food).
           - If "The Trendsetter" or "The Shopper", challenge: "No New Clothes" (Category: Clothing & Apparel).
           - If they have many recurring bills, challenge: "No New Subscriptions" (Category: Utilities or Entertainment).
        2. Assign a 'duration_days' (Integer 1-30) based on difficulty.
           - Hardier habits = shorter duration first.
           - General savings = longer duration.
        3. Title must be catchy/fun.
        4. CRITICAL: For 'NO_SPEND_CATEGORY', you MUST use one of the EXACT categories from this list:
           ['Housing', 'Utilities', 'Food', 'Transportation', 'Healthcare', 'Personal Care', 'Entertainment', 'Clothing & Apparel', 'Groceries', 'Tax', 'Other'].
           Do NOT use generic terms like "Shopping" or "Dining". Use the closest match from the list.
        
        Output JSON Object (Single Item):
        {{
            "title": "Starbucks Fast",
            "description": "Save $20 by making coffee at home.",
            "type": "NO_SPEND_CATEGORY", 
            "target_variable": {{"target_category": "Food"}}, 
            "duration_days": 3,
            "reward_points": 300,
            "reward_xp": 100,
            "difficulty": "Rare"
        }}
        
        Valid Types: 'NO_SPEND_CATEGORY', 'NO_SPEND_VENDOR', 'SAVE_AMOUNT'.
        """

        # 3. Call Gemini
        if not settings.GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY not set. Using fallback.")
            # raise Exception("No API Key") # Don't raise, just fall back
            return [{ 
                'title': 'The 3-Day Saver', 'description': 'Save at least ₹500/day for 3 days.', 
                'difficulty': 'Common', 'reward_points': 300, 'reward_xp': 150,
                'type': 'SAVE_AMOUNT', 'target_variable': {'amount': 500}, 'duration_days': 3
            }]

        # Debug: Print first few chars of key to confirm it's loaded
        key_suffix = settings.GOOGLE_API_KEY[:4] + "..." if settings.GOOGLE_API_KEY else "None"
        print(f"DEBUG: Using Google API Key starting with: {key_suffix}")
            
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # Switched to 1.5-flash for better free tier quota
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        
        challenge = json.loads(text)
        
        # Ensure it's a list for compatibility or handle single object (we want single now)
        if isinstance(challenge, list):
            challenge = challenge[0]
            
        # --- SANITIZATION STEP ---
        # AI often hallucinates categories like "Shopping" or "Dining". We must map them to valid DB choices.
        valid_categories = [c[0] for c in Transaction.CATEGORY_CHOICES]
        target_var = challenge.get('target_variable', {})
        t_cat = target_var.get('target_category')
        
        if t_cat:
            # 1. Direct Match?
            if t_cat in valid_categories:
                pass # Good
            else:
                # 2. Map known hallucinations
                print(f"DEBUG: AI generated invalid category: '{t_cat}'. Attempting fix...")
                if t_cat in ['Shopping', 'Retail', 'Clothes']: 
                    target_var['target_category'] = 'Clothing & Apparel'
                elif t_cat in ['Dining', 'Restaurants', 'Eating Out']:
                    target_var['target_category'] = 'Food'
                elif t_cat in ['Gas', 'Fuel']:
                    target_var['target_category'] = 'Transportation'
                else:
                    # 3. Fallback: Check for partial case-insensitive match
                    found = False
                    for valid in valid_categories:
                        if valid.lower() == t_cat.lower():
                            target_var['target_category'] = valid
                            found = True
                            break
                    if not found:
                        # 4. Final Fallback
                        print(f"DEBUG: Could not map '{t_cat}'. Defaulting to 'Other'.")
                        target_var['target_category'] = 'Other'
            
            # Save back
            challenge['target_variable'] = target_var
            # --- END SANITIZATION ---
            
        return [challenge] # Return as list to match expectation of view/iterator logic temporarily


    except Exception as e:
        logger.error(f"Error generating AI quests: {e}")
        # Fallback quests if AI fails
        return [
            { 
                'title': 'The 3-Day Saver', 'description': 'Save at least ₹500/day for 3 days.', 
                'difficulty': 'Common', 'reward_points': 300, 'reward_xp': 150,
                'type': 'SAVE_AMOUNT', 'target_variable': {'amount': 500}, 'duration_days': 3
            }
        ]

# ==========================================
# VIEWS & HELPERS
# ==========================================

def _generate_challenge_internal(user):
    """Helper to generate and save a challenge"""
    try:
        new_quests_data = generate_personalized_quests(user) # Returns list [challenge]
        for q_data in new_quests_data:
            DailyQuest.objects.create(
                user=user,
                title=q_data.get('title', 'Weekly Challenge'),
                description=q_data.get('description', 'Complete this task'),
                quest_type=q_data.get('type', 'OTHER'),
                reward_points=q_data.get('reward_points', 10),
                reward_xp=q_data.get('reward_xp', 50),
                difficulty=q_data.get('difficulty', 'Common'),
                target_variable=q_data.get('target_variable', {}),
                duration_days=q_data.get('duration_days', 7),
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=q_data.get('duration_days', 7)),
                status='ACTIVE'
            )
    except Exception as e:
        print(f"Error Gen Challenge: {e}")

@login_required
def gamification_view(request):
    user = request.user
    context = {}
    
    try:
        # 1. Check Streak
        check_daily_streak(user)
        
        # 2. Get Profile
        gamification_profile, _ = GamificationProfile.objects.get_or_create(user=user)
        
        # 3. Get LATEST Challenge (Any status)
        active_challenge = DailyQuest.objects.filter(user=user).order_by('-start_date').first()
        
        should_generate = False
        if not active_challenge:
            should_generate = True
        elif active_challenge.end_date < timezone.now():
            # If expired, we can generate a new one
            should_generate = True
            
        # If we need a new one, generate it
        if should_generate:
             # Check if we completed one today? If so, maybe wait? 
             # For now, auto-generate if none exists.
            _generate_challenge_internal(user)
            active_challenge = DailyQuest.objects.filter(user=user, status='ACTIVE').first()

        # 4. Update Status (Check progress)
        update_quest_status(user)
        
        # 5. Leaderboard Data
        leaderboard = GamificationProfile.objects.select_related('user').order_by('-total_xp')[:10]
        
        context['gamification_profile'] = gamification_profile
        context['active_challenge'] = active_challenge
        context['leaderboard'] = leaderboard
        
    except Exception as e:
        print(f"Gamification View Error: {e}")
        
    return render(request, 'dashboard/gamification.html', context)

@login_required
def generate_challenge_view(request):
    """Manual trigger to generate a new challenge (skips old one)"""
    if request.method == 'POST':
        # Mark existing active as FAILED or just reset?
        # Let's delete or mark FAILED. User wants a new one.
        DailyQuest.objects.filter(user=request.user, status='ACTIVE').update(status='FAILED')
        
        _generate_challenge_internal(request.user)
        
    return redirect('dashboard:gamification')
