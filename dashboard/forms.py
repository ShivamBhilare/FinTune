from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal
from .models import Transaction

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['vendor_name', 'amount', 'category', 'transaction_type', 'description', 'is_external']
        widgets = {
            'vendor_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Walmart'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'is_external': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 rounded'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-input'}),
        }

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(TransactionForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        txn_type = cleaned_data.get('transaction_type')
        is_external = cleaned_data.get('is_external')

        # Logic: Prevent spending money you don't have
        if amount and txn_type in ['EXPENSE', 'INVESTMENT'] and not is_external:
            current_balance = self.get_wallet_balance()
            if amount > current_balance:
                raise ValidationError(
                    f"Insufficient Funds! Balance: ₹{current_balance}. Check 'External' if this money is outside wallet."
                )
        return cleaned_data

    def get_wallet_balance(self):
        # 1. Get Initial Balance from Profile
        try:
            initial_balance = self.user.profile.cash_balance or Decimal(0)
        except Exception:
            initial_balance = Decimal(0)

        # 2. Add Incomes
        incomes = Transaction.objects.filter(
            user=self.user, 
            transaction_type='INCOME', 
            is_external=False
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

        # 3. Subtract Expenses
        expenses = Transaction.objects.filter(
            user=self.user, 
            transaction_type__in=['EXPENSE', 'INVESTMENT'], 
            is_external=False
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

        # 4. Return Total
        return initial_balance + incomes - expenses