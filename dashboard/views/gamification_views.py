from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from dashboard.models import GamificationProfile, DailyQuest
from dashboard.utils_challenges import check_daily_streak, update_quest_status
from dashboard.utils_ai_quests import generate_personalized_quests

@login_required
def gamification_view(request):
    user = request.user
    context = {}
    
    try:
        # 1. Check Streak
        check_daily_streak(user)
        
        # 2. Get Profile
        gamification_profile, _ = GamificationProfile.objects.get_or_create(user=user)
        
        # 3. Get ACTIVE Challenge (One at a time)
        active_challenge = DailyQuest.objects.filter(user=user, status='ACTIVE').first()
        
        # If no active challenge, we generate one automatically (or user can manually do it)
        if not active_challenge:
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
                end_date=timezone.now() + timezone.timedelta(days=q_data.get('duration_days', 7)),
                status='ACTIVE'
            )
    except Exception as e:
        print(f"Error Gen Challenge: {e}")
