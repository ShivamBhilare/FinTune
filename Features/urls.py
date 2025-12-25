from django.urls import path
from .views import dashboard_views, addTransaction_views, bugetGenerator_views, pattern_views, goal_views

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
    # Goal Path Simulator
    path('goal-simulator/', goal_views.goal_tracker_view, name='goal_tracker'),
    path('goal-simulator/save/', goal_views.save_goal, name='save_goal'),
    path('goal-simulator/delete/<int:pk>/', goal_views.delete_goal, name='delete_goal'),
    path('goal-simulator/calculate/', goal_views.calculate_goal_projection, name='calculate_goal_projection'),
    path('goal-simulator/insights/', goal_views.get_financial_insights, name='get_financial_insights'),
]
