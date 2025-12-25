from django.urls import path
from .views import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.dashboard_view, name='home'),
    path('dashboard/', dashboard_views.dashboard_view, name='dashboard_main'),
    path('profile/', dashboard_views.profile_view, name='profile'),
]
