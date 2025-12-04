from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('vendor_name', 'amount', 'category', 'transaction_type', 'date', 'user')
    list_filter = ('transaction_type', 'category', 'input_source', 'date')
    search_fields = ('vendor_name', 'amount')
