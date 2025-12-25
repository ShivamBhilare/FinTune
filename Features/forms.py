from django import forms
from django.contrib.auth.models import User
from auth_user.models import UserProfile

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'input-field w-full px-4 py-3 rounded-xl text-sm'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'input-field w-full px-4 py-3 rounded-xl text-sm'})
    )

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'monthly_income', 'cash_balance', 'total_liabilities']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'input-field w-full pl-12 pr-4 py-3 rounded-xl text-sm'}),
            'monthly_income': forms.NumberInput(attrs={'class': 'input-field w-full pl-10 pr-4 py-3 rounded-xl text-sm'}),
            'cash_balance': forms.NumberInput(attrs={'class': 'input-field w-full pl-10 pr-4 py-3 rounded-xl text-sm'}),
            'total_liabilities': forms.NumberInput(attrs={'class': 'input-field w-full pl-10 pr-4 py-3 rounded-xl text-sm text-rose-200'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            profile.save()
        return profile
from .models import Transaction

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['vendor_name', 'amount', 'category', 'transaction_type', 'description', 'is_external']
        
        widgets = {
            'vendor_name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-yellow-400 placeholder-slate-400',
                'placeholder': 'e.g. Walmart'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-yellow-400',
                'step': '0.01'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-yellow-400'
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-yellow-400'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-yellow-400 placeholder-slate-400',
                'rows': 2
            }),
            'is_external': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-yellow-400 bg-slate-700 border-slate-600 rounded focus:ring-yellow-400 focus:ring-2'
            })
        }
