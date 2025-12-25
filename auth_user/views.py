from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile
from .forms import QuestionnaireForm

@login_required
def questionnaire_view(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if profile.is_onboarded:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        form = QuestionnaireForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.is_onboarded = True
            profile.save()
            messages.success(request, "Profile updated successfully! Welcome to your dashboard.")
            return redirect('dashboard:dashboard')
    else:
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        }
        form = QuestionnaireForm(instance=profile, initial=initial_data)

    return render(request, 'auth_user/questionnaire.html', {'form': form})
