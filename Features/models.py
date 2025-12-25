from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('INVESTMENT', 'Investment'),
        ('DEBT_PAYMENT', 'Debt Payment')
    ]

    CATEGORY_CHOICES = [
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
        ('Savings', 'Savings'),
        ('Liabilities', 'Liabilities'),
        ('Other', 'Other')
    ]

    INPUT_SOURCES = [
        ('MANUAL', 'Manual'),
        ('VOICE', 'Voice'),
        ('IMAGE', 'Image')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    vendor_name = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='EXPENSE')
    date = models.DateField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    input_source = models.CharField(max_length=10, choices=INPUT_SOURCES, default='MANUAL')
    is_external = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type}: {self.amount} - {self.vendor_name}"

class FinancialGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_goals')
    name = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_contribution = models.DecimalField(max_digits=10, decimal_places=2)
    target_date = models.DateField()
    risk_profile = models.CharField(max_length=20, default='MEDIUM')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GamificationProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='gamification_profile')
    points = models.IntegerField(default=0)
    total_xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    current_streak = models.IntegerField(default=0)
    last_streak_update = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Level {self.level}"

class DailyQuest(models.Model):
    QUEST_STATUS = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quests')
    title = models.CharField(max_length=255)
    description = models.TextField()
    quest_type = models.CharField(max_length=50, default='OTHER') # NO_SPEND_CATEGORY, SAVE_AMOUNT, etc.
    reward_points = models.IntegerField(default=10)
    reward_xp = models.IntegerField(default=50)
    difficulty = models.CharField(max_length=20, default='Common')
    target_variable = models.JSONField(default=dict) # Stores target_category, amount, etc.
    duration_days = models.IntegerField(default=1)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=QUEST_STATUS, default='ACTIVE')
    current_progress = models.IntegerField(default=0) # e.g. days completed

    def __str__(self):
        return f"{self.title} ({self.status})"
