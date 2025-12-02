from django.urls import path
from .views import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.home, name='home'),
]
