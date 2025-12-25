from django.urls import path
from .views import dashboard_views

urlpatterns = [
    path('', dashboard_views.home_redirect_view, name='home'),
    path('dashboard/', dashboard_views.dashboard_view, name='dashboard'),
]
