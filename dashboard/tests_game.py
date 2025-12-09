from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from dashboard.models import Transaction, GamificationProfile
from auth_user.models import UserProfile
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

class GamificationTests(TestCase):
    def setUp(self):
        # Create User
        self.user = User.objects.create_user(username='testuser', password='password')
        # Profile created by signal
        self.profile = self.user.profile
        self.profile.monthly_income = 3000
        self.profile.fixed_expenses = 0
        self.profile.save()
        
        # Ensure GamificationProfile exists
        GamificationProfile.objects.get_or_create(user=self.user) 
        # Daily Budget = (3000-0)/30 = 100
        
        self.client = Client()
        self.client.login(username='testuser', password='password')
        
    def test_streak_calculation_under_budget(self):
        # Spend 50 (Under 100) -> Streak should be 1
        Transaction.objects.create(
            user=self.user, 
            amount=50, 
            transaction_type='EXPENSE', 
            category='Entertainment' # Discretionary
        )
        
        response = self.client.get(reverse('dashboard:gamification'))
        self.assertEqual(response.status_code, 200)
        
        gp = GamificationProfile.objects.get(user=self.user)
        self.assertEqual(gp.streak, 1)

    def test_streak_calculation_over_budget(self):
        # Spend 150 (Over 100) -> Streak should be 0
        Transaction.objects.create(
            user=self.user, 
            amount=150, 
            transaction_type='EXPENSE', 
            category='Entertainment'
        )
        
        response = self.client.get(reverse('dashboard:gamification'))
        gp = GamificationProfile.objects.get(user=self.user)
        self.assertEqual(gp.streak, 0)

    def test_streak_ignores_needs(self):
        # Spend 200 on Needs (Housing) -> Should be ignored
        # Spend 0 Discretionary -> Under 100 -> Streak 1
        Transaction.objects.create(
            user=self.user, 
            amount=200, 
            transaction_type='EXPENSE', 
            category='Housing' 
        )
        
        response = self.client.get(reverse('dashboard:gamification'))
        gp = GamificationProfile.objects.get(user=self.user)
        self.assertEqual(gp.streak, 1) # Ignored the housing cost

    def test_accept_challenge_api(self):
        response = self.client.post(reverse('dashboard:accept_challenge', args=['test_quest']))
        self.assertEqual(response.status_code, 200)
        
        gp = GamificationProfile.objects.get(user=self.user)
        self.assertEqual(gp.active_challenge_id, 'test_quest')

    def test_complete_challenge_api(self):
        # First accept
        gp = self.user.gamification_profile
        gp.active_challenge_id = 'test_quest'
        gp.save()
        
        # Complete
        response = self.client.post(
            reverse('dashboard:complete_challenge'),
            data={'xp': 100, 'coins': 500},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        gp.refresh_from_db()
        self.assertEqual(gp.xp, 100)
        self.assertEqual(gp.coins, 500)
        self.assertEqual(gp.active_challenge_id, '')
        self.assertIn('test_quest', gp.completed_challenges_ids)

    def test_get_challenge_progress(self):
        from dashboard.utils_challenges import get_challenge_progress
        from django.utils import timezone
        import datetime

        # Create saved transactions for savings
        Transaction.objects.create(
            user=self.user,
            amount=300,
            transaction_type='EXPENSE', # Technically savings might be transfer or expense, cat matters
            category='Savings',
            date=timezone.now()
        )

        # Test SAVE_AMOUNT progress
        # Use simple now - 1h as start time
        start_time = timezone.now() - datetime.timedelta(hours=1)
        progress = get_challenge_progress(
            self.user, 
            'SAVE_AMOUNT', 
            target_amount=1000, 
            start_time=start_time
        )
        
        # 300 / 1000 = 30%
        self.assertEqual(progress['current'], 300)
        self.assertEqual(progress['percentage'], 30)
        self.assertFalse(progress['is_completed'])
        
        # Add more savings to complete
        Transaction.objects.create(
            user=self.user,
            amount=800,
            category='Investment',
            date=timezone.now()
        )
        
        progress = get_challenge_progress(
            self.user, 
            'SAVE_AMOUNT', 
            target_amount=1000, 
            start_time=start_time
        )
        # 1100 / 1000 = 100% (capped)
        self.assertEqual(progress['current'], 1100)
        self.assertEqual(progress['percentage'], 100)
        self.assertTrue(progress['is_completed'])
