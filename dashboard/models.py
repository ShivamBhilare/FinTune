from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Transaction(models.Model):
    # Enums
    TRANSACTION_TYPES = [('INCOME', 'Income'), ('EXPENSE', 'Expense')]
    INPUT_SOURCES = [('MANUAL', 'Manual'), ('VOICE', 'Voice'), ('CAMERA', 'Camera')]
    
    # Updated Categories per request
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
        ('Other', 'Other')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    vendor_name = models.CharField(max_length=100, help_text="e.g. Starbucks, Amazon")
    
    # Using the display name as value for simplicity in AI mapping, 
    # but strictly max_length needs to accommodate the longest string
    category = models.CharField(max_length=50, choices=CATEGORIES, default='Other')
    transaction_type = models.CharField(max_length=7, choices=TRANSACTION_TYPES, default='EXPENSE')
    date = models.DateTimeField(default=timezone.now)
    
    description = models.CharField(max_length=255, blank=True, null=True) # Added for AI descriptions
    input_source = models.CharField(max_length=10, choices=INPUT_SOURCES, default='MANUAL')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor_name} - {self.amount}"