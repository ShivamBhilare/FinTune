from django.db import models
from django.contrib.auth.models import User
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
        ('Investment', 'Investment'), # <--- Added this
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