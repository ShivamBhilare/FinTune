from django.urls import path
from dashboard.views import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.home, name='home'),
    path('history/', dashboard_views.transaction_history, name='transaction_history'),
    path('add-manual/', dashboard_views.add_manual_transaction, name='add_manual'),
    path('process-voice/', dashboard_views.process_voice_input, name='process_voice'),
    path('save-confirmed/', dashboard_views.save_confirmed_transactions, name='save_confirmed'),
]