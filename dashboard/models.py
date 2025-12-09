from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class Transaction(models.Model):
    # 1. Add INVESTMENT to types
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'), 
        ('EXPENSE', 'Expense'), 
        ('INVESTMENT', 'Investment') # New Type
    ]
    
    INPUT_SOURCES = [('MANUAL', 'Manual'), ('VOICE', 'Voice'), ('CAMERA', 'Camera')]
    
    # 2. Add 'Investment' to categories so the dropdown has it
    CATEGORIES = [
        ('Housing', 'Housing'),
        ('Utilities', 'Utilities'),
        ('Food', 'Food'),
        ('Transportation', 'Transportation'),
        ('Healthcare', 'Healthcare'),
        ('Personal Care', 'Personal Care'),
        ('Entertainment', 'Entertainment'),
        ('Clothing & Apparel', 'Clothing & Apparel'),
        ('Groceries', 'Groceries'),
        ('Tax', 'Tax'),
        ('Investment', 'Investment'), 
        ('Savings', 'Savings'), # <--- Added this
        ('Other', 'Other')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    vendor_name = models.CharField(max_length=100, help_text="e.g. Starbucks, Amazon")
    
    category = models.CharField(max_length=50, choices=CATEGORIES, default='Other')
    
    # CRITICAL FIX: Increased max_length to 20 (was 7) to hold 'INVESTMENT'
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='EXPENSE')
    
    date = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=255, blank=True, null=True)
    input_source = models.CharField(max_length=10, choices=INPUT_SOURCES, default='MANUAL')


    # 3. New Logic Field: External Transactions
    is_external = models.BooleanField(
        default=False,
        verbose_name="External Transaction (Don't affect Balance)"
    )

    # 4. Gamification Lock
    verified_quest_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID of the quest this transaction verified. Prevents deletion abuse.")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor_name} - {self.amount}"

class QuestLog(models.Model):
    """
    Stores a permanent history of completed quests.
    Replaces the simple 'completed_challenges_ids' text string.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quest_logs')
    quest_id = models.CharField(max_length=100) # The AI generated ID or fallback ID
    title = models.CharField(max_length=255)
    description = models.TextField()
    xp_earned = models.IntegerField()
    coins_earned = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)
    quest_type = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class FinancialGoal(models.Model):
    RISK_PROFILES = [
        ('LOW', 'Low (Conservative)'),
        ('MEDIUM', 'Medium (Balanced)'),
        ('HIGH', 'High (Aggressive)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_goals')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_contribution = models.DecimalField(max_digits=10, decimal_places=2)
    target_date = models.DateField()
    risk_profile = models.CharField(max_length=10, choices=RISK_PROFILES, default='MEDIUM')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_risk_profile_display()})"

class GamificationProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='gamification_profile')
    xp = models.IntegerField(default=0)
    coins = models.IntegerField(default=0)
    streak = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    
    # Store active challenge ID (simple string/integer approach for now)
    active_challenge_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Store completed challenges as a JSON-like text or related model. 
    # For simplicity, let's use a standard TextField storing comma-separated IDs 
    # or a JSONField if we were sure about the DB support (SQLite/Postgres). 
    # We'll use a text field for compatibility.
    completed_challenges_ids = models.TextField(default="", blank=True) 

    last_streak_update = models.DateField(blank=True, null=True)

    # New Fields for AI Quests
    daily_quests = models.TextField(default="[]", blank=True, help_text="JSON list of daily quests")
    last_daily_quest_refresh = models.DateField(blank=True, null=True)
    # Track when the current quest was accepted to verify actions *after* this time
    challenge_accepted_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - Level {self.level}"

@receiver(post_save, sender=User)
def create_gamification_profile(sender, instance, created, **kwargs):
    if created:
        GamificationProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_gamification_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'gamification_profile'):
         GamificationProfile.objects.create(user=instance)
    if not hasattr(instance, 'gamification_profile'):
         GamificationProfile.objects.create(user=instance)
    instance.gamification_profile.save()

# Import signals to ensure they are registered
import dashboard.signals