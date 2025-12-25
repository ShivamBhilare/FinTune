from django.shortcuts import render
from django.contrib.auth.decorators import login_required

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
