from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class QuestionnaireForm(forms.ModelForm):
    # We include User fields here explicitly to save them together
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'monthly_income', 'cash_balance', 'fixed_expenses']

    def save(self, commit=True):
        # 1. Save Profile Data
        profile = super().save(commit=False)
        
        # 2. Save User Data (First/Last Name)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            profile.save()
            
        return profile