from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.



class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('INVESTMENT', 'Investment')
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
