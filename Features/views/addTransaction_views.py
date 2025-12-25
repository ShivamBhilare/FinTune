from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
import json
from decimal import Decimal
from ..models import Transaction
from ..forms import TransactionForm
from ..utils import process_voice_with_gemini, process_image_with_gemini
from auth_user.models import UserProfile

@login_required
@require_POST
def add_manual_transaction(request):
    form = TransactionForm(request.POST)
    if form.is_valid():
        transaction = form.save(commit=False)
        transaction.user = request.user
        transaction.input_source = 'MANUAL'
        
        # Balance Check Logic
        profile = request.user.profile
        amount = transaction.amount
        
        if not transaction.is_external:
             pass # Logic removed: Cash balance is now static initial balance

            
        transaction.save()
        return JsonResponse({'status': 'success', 'message': 'Transaction added successfully!'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid form data', 'errors': form.errors})

@login_required
@require_POST
def process_voice(request):
    try:
        data = json.loads(request.body)
        transcript = data.get('transcript')
        if not transcript:
            return JsonResponse({'status': 'error', 'message': 'No transcript provided'})
            
        result = process_voice_with_gemini(transcript)
        if "error" in result:
             return JsonResponse({'status': 'error', 'message': 'AI Processing Failed'})
             
        return JsonResponse({'status': 'success', 'data': result})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_POST
def process_image(request):
    if 'image' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No image provided'})
        
    image_file = request.FILES['image']
    result = process_image_with_gemini(image_file)
    
    if "error" in result:
         return JsonResponse({'status': 'error', 'message': 'AI Processing Failed'})
         
    return JsonResponse({'status': 'success', 'data': result})

@login_required
@require_POST
def save_confirmed(request):
    try:
        data = json.loads(request.body)
        transactions_data = data.get('transactions', [])
        is_external_global = data.get('is_external', False)
        
        profile = request.user.profile
        total_expense = 0
        total_income = 0
        
        # First pass: Calculate totals for balance check
        for item in transactions_data:
            amount = float(item.get('amount', 0))
            t_type = item.get('type', 'EXPENSE').upper() # Ensure consistent casing
            
            if t_type in ['EXPENSE', 'INVESTMENT']:
                total_expense += amount
            elif t_type == 'INCOME':
                total_income += amount
                
        # Check balance if not external
        # Balance Check Removed: cash_balance is static


        # Second pass: Save transactions
        transactions_to_create = []
        for item in transactions_data:
            t = Transaction(
                user=request.user,
                vendor_name=item.get('vendor', 'Unknown'),
                amount=item.get('amount', 0),
                category=item.get('category', 'Other'),
                transaction_type=item.get('type', 'EXPENSE').upper(),
                description=item.get('description', ''),
                input_source=item.get('source', 'MANUAL'),
                is_external=is_external_global
            )
            transactions_to_create.append(t)
            
        Transaction.objects.bulk_create(transactions_to_create)
        
        # Update Balance
        # Update Balance Removed: cash_balance is static

            
        return JsonResponse({'status': 'success', 'message': f'{len(transactions_to_create)} transactions saved!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
