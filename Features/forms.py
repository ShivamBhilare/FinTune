from django import forms
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
