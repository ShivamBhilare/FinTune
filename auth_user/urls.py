from django.urls import path
from . import views

urlpatterns = [
    # This registers the URL: http://127.0.0.1:8000/onboarding/
    path('onboarding/', views.questionnaire_view, name='questionnaire'),
]