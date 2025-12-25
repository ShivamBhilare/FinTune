from django.urls import path
from . import dashboard_views

urlpatterns = [
    path('', dashboard_views.home_redirect_view, name='home'),
    # Mapping 'questionnaire' to match LOGIN_REDIRECT_URL = 'questionnaire'
    path('questionnaire/', dashboard_views.questionnaire_view, name='questionnaire'),
    path('dashboard/', dashboard_views.dashboard_view, name='dashboard'),
]
