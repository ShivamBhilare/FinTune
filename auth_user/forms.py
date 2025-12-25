from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class QuestionnaireForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 text-white placeholder-slate-400'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 text-white placeholder-slate-400'}))

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'monthly_income', 'cash_balance', 'total_liabilities']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 text-white placeholder-slate-400'}),
            'monthly_income': forms.NumberInput(attrs={'class': 'w-full pl-8 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 text-white placeholder-slate-400'}),
            'cash_balance': forms.NumberInput(attrs={'class': 'w-full pl-8 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 text-white placeholder-slate-400'}),
            'total_liabilities': forms.NumberInput(attrs={'class': 'w-full pl-8 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 text-white placeholder-slate-400'}),
        }

    def save(self, commit=True):
        user = self.instance.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return super().save(commit=commit)
