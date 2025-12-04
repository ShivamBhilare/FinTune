from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Transaction(models.Model):
    # Enums
    TRANSACTION_TYPES = [('INCOME', 'Income'), ('EXPENSE', 'Expense')]
    INPUT_SOURCES = [('MANUAL', 'Manual'), ('VOICE', 'Voice'), ('CAMERA', 'Camera')]
    
    # Simple Categories (You can expand this list later)
    CATEGORIES = [
        ('FOOD', 'Food'), ('TRAVEL', 'Travel'), ('SHOPPING', 'Shopping'),
        ('BILLS', 'Bills'), ('ENTERTAINMENT', 'Entertainment'), ('OTHER', 'Other')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    vendor_name = models.CharField(max_length=100, help_text="e.g. Starbucks, Amazon")
    
    category = models.CharField(max_length=20, choices=CATEGORIES, default='OTHER')
    transaction_type = models.CharField(max_length=7, choices=TRANSACTION_TYPES, default='EXPENSE')
    date = models.DateTimeField(default=timezone.now)
    
    input_source = models.CharField(max_length=10, choices=INPUT_SOURCES, default='MANUAL')
    is_recurring = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor_name} - {self.amount}"
