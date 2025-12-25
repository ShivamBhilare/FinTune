from django.urls import path
from .views import dashboard_views, addTransaction_views

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.dashboard_view, name='home'),
    path('dashboard/', dashboard_views.dashboard_view, name='dashboard_main'),
    path('profile/', dashboard_views.profile_view, name='profile'),
    path('', dashboard_views.home_redirect_view, name='home'),
    path('dashboard/', dashboard_views.dashboard_view, name='dashboard'),
    
    # Add Transaction Endpoints
    path('add-manual/', addTransaction_views.add_manual_transaction, name='add_manual'),
    path('process-voice/', addTransaction_views.process_voice, name='process_voice'),
    path('process-image/', addTransaction_views.process_image, name='process_image'),
    path('save-confirmed/', addTransaction_views.save_confirmed, name='save_confirmed'),
]
