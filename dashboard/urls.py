from django.urls import path
from dashboard.views import dashboard_views
from dashboard.views import transactions_views
from dashboard.views import addTransaction_views
from dashboard.views import budgetGen_views
app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.home, name='home'),
    path('history/', transactions_views.transaction_history, name='transaction_history'),
    path('add-manual/', addTransaction_views.add_manual_transaction, name='add_manual'),
    path('process-voice/', addTransaction_views.process_voice_input, name='process_voice'),
    path('process-image/', addTransaction_views.process_image_input, name='process_image'),
    path('save-confirmed/', addTransaction_views.save_confirmed_transactions, name='save_confirmed'),
    path('budget-generator/', budgetGen_views.budget_generator_view, name='budget_generator'),
]