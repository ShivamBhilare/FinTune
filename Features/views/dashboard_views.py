from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..forms import ProfileForm

@login_required
def profile_view(request):
    """
    Profile management view.
    Allows users to view and update their profile information.
    """
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return render(request, 'dashboard/profile.html', {'form': form, 'success': True})
    else:
        form = ProfileForm(instance=request.user.profile)
    
    return render(request, 'dashboard/profile.html', {'form': form})

@login_required
def dashboard_view(request):
    """
    Main dashboard view.
    Redirects here after login.
    """
    return render(request, 'dashboard/home.html')

@login_required
def questionnaire_view(request):
    """
    Questionnaire view.
    Redirects here if LOGIN_REDIRECT_URL is set to 'questionnaire'.
    """
    return render(request, 'account/questionnaire.html')

def home_redirect_view(request):
    """
    Root URL view.
    Redirects to questionnaire if logged in, else to login page.
    """
    from django.shortcuts import redirect
    if request.user.is_authenticated:
        return redirect('questionnaire')
    return redirect('account_login')
