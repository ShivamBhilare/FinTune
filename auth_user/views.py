from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import QuestionnaireForm

@login_required
def questionnaire_view(request):
    """
    View to handle first-time onboarding.
    Accessible only if user.profile.is_onboarded is False.
    """
    profile = request.user.profile

    # 1. THE GATEKEEPER LOGIC
    # If they already did this, kick them to the dashboard/home immediately.
    if profile.is_onboarded:
        return redirect('dashboard:home') # Change 'dashboard' to your actual home URL name

    if request.method == 'POST':
        form = QuestionnaireForm(request.POST, instance=profile)
        if form.is_valid():
            # Save the data
            form.save()
            
            # 2. LOCK THE DOOR
            # Mark as onboarded so they never see this page again
            profile.is_onboarded = True
            profile.save()
            
            messages.success(request, "Profile setup complete! Welcome.")
            return redirect('dashboard:home') # Redirect to main app
    else:
        # Pre-fill fields if they exist
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name
        }
        form = QuestionnaireForm(instance=profile, initial=initial_data)

    return render(request, 'account/questionnaire.html', {'form': form})