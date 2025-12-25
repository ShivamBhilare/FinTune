from django.urls import path
from .views import dashboard_views, addTransaction_views, bugetGenerator_views, pattern_views, gamification_views

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.home_redirect_view, name='home'),
    path('profile/', dashboard_views.profile_view, name='profile'),
    path('history/', dashboard_views.transaction_history, name='history'),
    path('dashboard/', dashboard_views.dashboard_view, name='dashboard'),
    
    # Add Transaction Endpoints
    path('add-manual/', addTransaction_views.add_manual_transaction, name='add_manual'),
    path('process-voice/', addTransaction_views.process_voice, name='process_voice'),
    path('process-image/', addTransaction_views.process_image, name='process_image'),
    path('save-confirmed/', addTransaction_views.save_confirmed, name='save_confirmed'),
    path('budget-generator/', bugetGenerator_views.budget_generator_view, name='budget_generator'),

    # Pattern Detection & ML Insights
    path('pattern-detection/', pattern_views.pattern_detection_view, name='pattern_detection'),

    # Gamification
    path('gamification/', gamification_views.gamification_view, name='gamification'),
    path('gamification/generate/', gamification_views.generate_challenge_view, name='generate_challenge'),
]
