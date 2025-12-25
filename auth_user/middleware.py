from django.shortcuts import redirect
from django.urls import reverse

class OnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            try:
                profile = request.user.profile
                if not profile.is_onboarded:
                    # List of paths exempt from redirection
                    exempt_paths = [
                        reverse('questionnaire'),
                        reverse('account_logout'),
                        # Add any other exempt paths here (e.g., static files if served by Django in dev)
                    ]
                    
                    if request.path not in exempt_paths and not request.path.startswith('/admin/') and not request.path.startswith('/static/') and not request.path.startswith('/accounts/'):
                         return redirect('questionnaire')
            except:
                # If profile doesn't exist for some reason, maybe let them proceed or handle gracefully
                # ideally signals should have created it.
                pass

        response = self.get_response(request)
        return response
