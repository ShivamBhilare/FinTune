from django.urls import path
from dashboard.views import dashboard_views
from dashboard.views import transactions_views
from dashboard.views import addTransaction_views
from dashboard.views import budgetGen_views
from dashboard.views import patternDetection_views
from dashboard.views import goalsimulator_views
from dashboard.views import game_views
app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.home, name='home'),
    path('history/', transactions_views.transaction_history, name='transaction_history'),
    path('add-manual/', addTransaction_views.add_manual_transaction, name='add_manual'),
    path('process-voice/', addTransaction_views.process_voice_input, name='process_voice'),
    path('process-image/', addTransaction_views.process_image_input, name='process_image'),
    path('save-confirmed/', addTransaction_views.save_confirmed_transactions, name='save_confirmed'),
    path('budget-generator/', budgetGen_views.budget_generator_view, name='budget_generator'),
    path('pattern-detection/', patternDetection_views.pattern_detection, name='pattern_detection'),
    # Goal Simulator
    path('goals/', goalsimulator_views.goal_tracker_view, name='goal_tracker'),
    path('goals/save/', goalsimulator_views.save_goal, name='save_goal'),
    path('goals/delete/<int:pk>/', goalsimulator_views.delete_goal, name='delete_goal'),
    path('goals/calculate/', goalsimulator_views.calculate_goal_projection, name='calculate_goal'),
    # Gamification
    path('gamification/', game_views.gamification_view, name='gamification'),
    path('gamification/accept/<str:challenge_id>/', game_views.accept_challenge, name='accept_challenge'),
    path('gamification/complete/', game_views.complete_challenge, name='complete_challenge'),
    path('gamification/leaderboard/', game_views.leaderboard_view, name='leaderboard'),
]