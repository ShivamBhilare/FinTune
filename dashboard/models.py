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

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor_name} - {self.amount}"



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


# --- GAMIFICATION MODELS ---

class GamificationProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='gamification_profile')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    total_xp = models.IntegerField(default=0)
    points = models.IntegerField(default=0) # Spendable 'FinCoins'
    level = models.IntegerField(default=1)
    
    last_quest_date = models.DateField(null=True, blank=True)
    last_streak_update = models.DateField(null=True, blank=True)
    
    savings_generated = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} - Lvl {self.level}"

@receiver(post_save, sender=User)
def create_gamification_profile(sender, instance, created, **kwargs):
    if created:
        GamificationProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_gamification_profile(sender, instance, **kwargs):
    # Check if profile exists before saving (for old users)
    if hasattr(instance, 'gamification_profile'):
        instance.gamification_profile.save()


class DailyQuest(models.Model):
    QUEST_TYPES = [
        ('NO_SPEND_CATEGORY', 'No Spend (Category)'),
        ('NO_SPEND_VENDOR', 'No Spend (Vendor)'),
        ('SAVE_AMOUNT', 'Save Amount'),
        ('STREAK_KEEPER', 'Streak Keeper'), # Legacy/Fallback
        ('OTHER', 'Other')
    ]
    
    QUEST_STATUS = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ]

    DIFFICULTY = [
        ('Basic', 'Basic'),
        ('Common', 'Common'),
        ('Rare', 'Rare'),
        ('Epic', 'Epic'),
        ('Legendary', 'Legendary')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_quests')
    title = models.CharField(max_length=100)
    description = models.TextField()
    quest_type = models.CharField(max_length=20, choices=QUEST_TYPES, default='OTHER')
    status = models.CharField(max_length=20, choices=QUEST_STATUS, default='ACTIVE')
    
    # Challenge Config
    duration_days = models.IntegerField(default=1) # 1 to 30
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(default=timezone.now)
    current_progress = models.IntegerField(default=0) # Days completed
    
    reward_points = models.IntegerField(default=10)
    reward_xp = models.IntegerField(default=50)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY, default='Common')
    
    # Stores target validation data e.g. {'category': 'Food', 'amount': 500}
    target_variable = models.JSONField(default=dict, blank=True)
    
    date_generated = models.DateField(auto_now_add=True)
    is_collected = models.BooleanField(default=False) # If user claimed reward

    def __str__(self):
        return f"{self.title} ({self.status}) - Day {self.current_progress}/{self.duration_days}"

