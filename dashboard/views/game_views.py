from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse
from dashboard.models import Transaction, GamificationProfile
from auth_user.models import UserProfile
from dashboard.utils_constants import NEEDS_CATEGORIES
import json
from datetime import timedelta

# --- HELPER FUNCTIONS ---

def calculate_level(xp):
    """
    Calculates level based on XP.
    Formula: Level = Floor(0.1 * Sqrt(XP)) + 1
    (Same as frontend logic to keep them in sync)
    """
    import math
    return math.floor(0.1 * math.sqrt(xp)) + 1

def calc_xp_for_next_level(level):
    return pow(level * 10, 2)

def check_badges(user):
    """
    Checks if user qualifies for any badges based on total savings/investments.
    (This can be expanded to return a list of earned badges)
    """
    # For now, we will just return total savings for the frontend to decide
    total_savings = Transaction.objects.filter(
        user=user, 
        transaction_type__in=['INVESTMENT', 'INCOME'], # Assuming purely savings/investment
        category__in=['Savings', 'Investment']
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    return total_savings

def calculate_streak(user):
    """
    Calculates and updates the daily streak.
    Logic:
    1. Get Income & Fixed Expenses from Profile.
    2. Calc Daily Discietionary Budget = (Income - Fixed Expenses) / 30.
    3. Get Today's Discretionary Spend (Exclude NEEDS_CATEGORIES).
    4. If Spend < Budget: Increment Streak (if not already updated today).
    5. If Spend > Budget: Reset Streak to 0.
    """
    try:
        profile = user.profile
        game_profile = user.gamification_profile
    except:
        return 0 # Fail safe

    # 1. Budget Calc
    income = profile.monthly_income or 0
    fixed = profile.fixed_expenses or 0
    daily_budget = (income - fixed) / 30
    
    if daily_budget <= 0:
         return game_profile.streak # Cannot calculate streak if no budget

    # 2. Today's Spend
    now = timezone.now()
    today_spend = Transaction.objects.filter(
        user=user,
        transaction_type='EXPENSE',
        date__date=now.date()
    ).exclude(category__in=NEEDS_CATEGORIES).aggregate(Sum('amount'))['amount__sum'] or 0

    # 3. Logic
    today_date = now.date()
    
    # Check if already updated today to avoid double counting or resetting on same day view
    if game_profile.last_streak_update == today_date:
        return game_profile.streak

    if today_spend < daily_budget:
        # Check if yesterday was missed (to reset if not consecutive)
        # Actually, simpler logic: 
        # If we are checking today, and we haven't updated today:
        # Did we miss yesterday? 
        # If last_update < yesterday, then streak is broken -> set to 0 (or 1 if today is good)
        
        last_update = game_profile.last_streak_update
        if last_update and (today_date - last_update).days > 1:
             game_profile.streak = 1 # Reset and start new
        else:
             game_profile.streak += 1
             
        game_profile.last_streak_update = today_date
        game_profile.save()
    elif today_spend > daily_budget:
        game_profile.streak = 0
        game_profile.last_streak_update = today_date
        game_profile.save()

    return game_profile.streak

# --- VIEWS ---

from dashboard.utils_ai_quests import generate_personalized_quests
from dashboard.utils_challenges import verify_challenge, get_challenge_progress
import json

@login_required
def gamification_view(request):
    user = request.user
    game_profile, created = GamificationProfile.objects.get_or_create(user=user)

    # 1. Update Streak
    streak = calculate_streak(user)
    
    # Load stored quests to check count
    try:
        stored_quests = json.loads(game_profile.daily_quests)
    except:
        stored_quests = []

    # 2. Daily Quest Refresh Logic
    # Refresh if:
    # a) It's a new day (IST)
    # b) We have fewer than 3 quests (Self-healing for falback/legacy data)
    now_date = timezone.localdate()
    
    should_refresh = (game_profile.last_daily_quest_refresh != now_date) or (len(stored_quests) < 3)

    if should_refresh:
        # Generate new AI quests (or fallback)
        new_quests = generate_personalized_quests(user)
        game_profile.daily_quests = json.dumps(new_quests)
        game_profile.last_daily_quest_refresh = now_date
        game_profile.save()
        stored_quests = new_quests # Update local var for context

    # 3. Calculate Progress for Active Quest
    active_progress = None
    if game_profile.active_challenge_id:
        active_quest = next((q for q in stored_quests if q['id'] == game_profile.active_challenge_id), None)
        if active_quest:
            active_progress = get_challenge_progress(
                user, 
                active_quest.get('type'), 
                target_category=active_quest.get('target_category'),
                target_amount=active_quest.get('target_amount'),
                target_time=active_quest.get('target_time'),
                start_time=game_profile.challenge_accepted_at
            )

    context = {
        'gamification_stats': {
            'xp': game_profile.xp,
            'coins': game_profile.coins,
            'level': calculate_level(game_profile.xp),
            'streak': streak,
            'nextLevelXp': calc_xp_for_next_level(calculate_level(game_profile.xp)),
            'activeChallengeId': game_profile.active_challenge_id or "",
            'activeProgress': active_progress, # New Data
            'completedChallenges': game_profile.completed_challenges_ids.split(',') if game_profile.completed_challenges_ids else [],
            'challenges': stored_quests # pass local var
        }
    }
    return render(request, 'dashboard/gamification.html', context)

@login_required
def accept_challenge(request, challenge_id):
    if request.method == 'POST':
        try:
            user = request.user
            gp, _ = GamificationProfile.objects.get_or_create(user=user)
            
            if gp.active_challenge_id:
                return JsonResponse({'status': 'error', 'message': 'You already have an active quest!'})
                
            gp.active_challenge_id = challenge_id
            gp.challenge_accepted_at = timezone.now() # START TIME
            gp.save()
            
            # Calculate Initial Progress (Likely 0, but good to be explicit)
            active_progress = None
            try:
                stored_quests = json.loads(gp.daily_quests)
                active_quest = next((q for q in stored_quests if q['id'] == challenge_id), None)
                if active_quest:
                    active_progress = get_challenge_progress(
                        user, 
                        active_quest.get('type'), 
                        target_category=active_quest.get('target_category'),
                        target_amount=active_quest.get('target_amount'),
                        target_time=active_quest.get('target_time'),
                        start_time=gp.challenge_accepted_at
                    )
            except:
                pass

            return JsonResponse({
                'status': 'success', 
                'message': 'Quest Accepted!',
                'active_progress': active_progress
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=400)

@login_required
def complete_challenge(request):
    if request.method == 'POST':
        try:
            user = request.user
            gp = user.gamification_profile
            
            # Find the active quest def
            try:
                daily_quests = json.loads(gp.daily_quests)
            except:
                daily_quests = []
                
            active_quest = next((q for q in daily_quests if q['id'] == gp.active_challenge_id), None)
            
            if not active_quest:
                return JsonResponse({'status': 'error', 'message': 'Active quest not found in daily pool.'})
            
            # VERIFY LOGIC
            is_valid = verify_challenge(
                user, 
                active_quest.get('type'), 
                target_category=active_quest.get('target_category'),
                target_amount=active_quest.get('target_amount'),
                target_time=active_quest.get('target_time'),
                start_time=gp.challenge_accepted_at # Pass start time
            )
            
            # Logic Note: NO_SPEND quests fail if they find a transaction.
            # verify_challenge returns True if Success (No Validation failure).
            # But wait: verify_challenge for NO_SPEND returns: "not exists" -> True if success.
            
            if not is_valid:
                return JsonResponse({'status': 'error', 'message': 'Quest conditions not met yet! Check your transactions.'})
                
            # --- 4. HARDENING: QUEST HISTORY & LOCKING ---
            from dashboard.models import QuestLog, Transaction
            
            # Create QuestLog (Permanent History)
            QuestLog.objects.create(
                user=user,
                quest_id=active_quest['id'],
                title=active_quest['title'],
                description=active_quest['description'],
                xp_earned=active_quest['rewardXP'],
                coins_earned=active_quest['rewardCoins'],
                quest_type=active_quest.get('type')
            )
            
            # Lock Transactions (Anti-Cheat)
            if active_quest.get('type') in ['SAVE_AMOUNT', 'TRANSACTION_BEFORE']:
                 txns = Transaction.objects.filter(user=user, date__gte=gp.challenge_accepted_at)
                 if active_quest.get('type') == 'SAVE_AMOUNT':
                     verifying_txns = txns.filter(category__in=['Savings', 'Investment'])
                     for t in verifying_txns:
                         t.verified_quest_id = active_quest['id']
                         t.save()
                 elif active_quest.get('type') == 'TRANSACTION_BEFORE':
                      for t in txns:
                          target_hour = active_quest.get('target_time')
                          if target_hour is not None and t.date.hour < target_hour:
                              t.verified_quest_id = active_quest['id']
                              t.save()
                              break

            # Award Rewards
            gp.xp += active_quest['rewardXP']
            gp.coins += active_quest['rewardCoins']
            
            # Check Level Up
            old_level = gp.level
            new_level = calculate_level(gp.xp)
            if new_level > old_level:
                gp.level = new_level
                # Could add specific notification here
            
            gp.active_challenge_id = "" # Clear active
            
            # Append to completed
            completed = gp.completed_challenges_ids.split(',') if gp.completed_challenges_ids else []
            completed.append(active_quest['id'])
            gp.completed_challenges_ids = ",".join(completed)
            
            gp.save()
            
            return JsonResponse({
                'status': 'success', 
                'new_xp': gp.xp, 
                'new_coins': gp.coins,
                'new_level': gp.level,
                'message': 'Quest Complete!'
            })
        except Exception as e:
            # print(e)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=400)

@login_required
def leaderboard_view(request):
    # Return top 5 users by XP
    top_profiles = GamificationProfile.objects.select_related('user').order_by('-xp')[:10]
    data = []
    for p in top_profiles:
        data.append({
            'name': p.user.username,
            'xp': p.xp,
            'level': calculate_level(p.xp),
            'streak': p.streak
        })
    return JsonResponse({'leaderboard': data})
