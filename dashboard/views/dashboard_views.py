import json
import os
import google.generativeai as genai
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dashboard.models import Transaction

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

@login_required
def home(request):
    user = request.user
    income = Transaction.objects.filter(user=user, transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
    expense = Transaction.objects.filter(user=user, transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = income - expense
    recent_transactions = Transaction.objects.filter(user=user).order_by('-date')[:5]
    
    context = {
        'total_balance': balance,
        'total_income': income,
        'total_expense': expense,
        'recent_transactions': recent_transactions
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    return render(request, 'dashboard/transaction_history.html', {'transactions': transactions})

@login_required
def add_manual_transaction(request):
    if request.method == "POST":
        amount = request.POST.get('amount')
        category = request.POST.get('category')
        vendor = request.POST.get('vendor')
        trans_type = request.POST.get('type') # INCOME or EXPENSE
        
        Transaction.objects.create(
            user=request.user,
            amount=amount,
            category=category,
            vendor_name=vendor,
            transaction_type=trans_type,
            input_source='MANUAL'
        )
        return redirect('dashboard:home')
    return redirect('dashboard:home')

@login_required
@csrf_exempt
def process_voice_input(request):
    """Sends transcript to Gemini and returns parsed JSON"""
    if request.method == "POST":
        data = json.loads(request.body)
        transcript = data.get('transcript')

        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        prompt = f"""
        You are an expert AI Transaction Categorizer. Your task is to analyze a text-based purchase receipt. The text will be generated from voice input (speech-to-text), and may contain small transcription errors. Your job is to accurately identify the vendor name, individual purchased items, and the price of each item.

        1. Input Format
        You will receive plain text containing: '{transcript}'
        
        2. Categorization Rules
        You must categorize each item into one of the following exact categories:
        [Housing, Utilities, Food, Transportation, Healthcare, Personal Care, Entertainment, Clothing & Apparel, Groceries, Tax, Other]
        If an item does not fit any category clearly, use "Other".
        If multiple items belong to the same category, merge them into a single category property and sum amounts belonging to the same item name when appropriate.

        output the vendor name in maximum 3 words or if not known than unknown.
        3. Output Requirements
        You must return ONLY a single JSON object.
        No explanation. No extra text. No comments. No calculations shown. Just JSON.
        Each category must contain an array of arrays.
        Each inner array must follow this format:
        ["Vendor/Store Name", Amount (number, two decimals, no currency symbol), "Description", "Income/Expense"]
        Only include categories that actually appear in the receipt.
        """

        try:
            response = model.generate_content(prompt)
            cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
            parsed_data = json.loads(cleaned_text)
            return JsonResponse({'status': 'success', 'data': parsed_data})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
@csrf_exempt
def save_confirmed_transactions(request):
    """Saves the JSON data after user confirmation, aggregating by category"""
    if request.method == "POST":
        try:
            payload = json.loads(request.body)
            categories_data = payload.get('data', {})

            for category, items in categories_data.items():
                total_amount = 0
                vendors = set()
                descriptions = []
                trans_type = "EXPENSE" # Default
                
                # Aggregation Logic
                for item in items:
                    # item format: ["Vendor", Amount, "Desc", "Type"]
                    vendor = item[0]
                    amount = float(item[1])
                    desc = item[2]
                    t_type = item[3].upper() # Ensure uppercase for DB

                    total_amount += amount
                    vendors.add(vendor)
                    descriptions.append(desc)
                    trans_type = t_type # Takes the last one, usually consistent per category group

                # Create merged Vendor name and Description
                merged_vendor = ", ".join(list(vendors))[:95] # Truncate to fit model
                merged_desc = ", ".join(descriptions)[:250]

                Transaction.objects.create(
                    user=request.user,
                    amount=total_amount,
                    category=category,
                    vendor_name=merged_vendor,
                    description=merged_desc,
                    transaction_type=trans_type, # Maps to INCOME/EXPENSE
                    input_source='VOICE'
                )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            print(e)
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error'})