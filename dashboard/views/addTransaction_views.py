from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from dashboard.models import Transaction
from dashboard.forms import TransactionForm 
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from decimal import Decimal
import json
import google.generativeai as genai
import os
from django.http import JsonResponse

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# --- 1. NEW MANUAL TRANSACTION VIEW ---
@login_required
def add_manual_transaction(request):
    try:
        if request.method == "POST":
            # Pass the user to the form so it can check balances
            form = TransactionForm(request.user, request.POST)
            
            if form.is_valid():
                transaction = form.save(commit=False)
                transaction.user = request.user
                transaction.input_source = 'MANUAL'
                transaction.save()
                return JsonResponse({'status': 'success'})
            else:
                # Extract the first error message clearly
                error_message = "Invalid Data"
                if form.non_field_errors():
                    error_message = form.non_field_errors()[0]
                else:
                    # Get the first field error
                    for field, errors in form.errors.items():
                        error_message = f"{field}: {errors[0]}"
                        break
                
                return JsonResponse({'status': 'error', 'message': error_message})
        
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    except Exception as e:
        # Catch any unexpected errors (DB, Logic, etc.)
        return JsonResponse({'status': 'error', 'message': f"System Error: {str(e)}"})

# --- 2. VOICE & IMAGE PROCESSORS (Keep your existing AI logic) ---
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
        [Housing, Utilities, Food, Transportation, Healthcare, Personal Care, Entertainment, Clothing & Apparel, Groceries, Tax, Salary, Investment, Savings, Other]
        If an item does not fit any category clearly, use "Other".
        If multiple items belong to the same category, merge them into a single category property and sum amounts belonging to the same item name when appropriate.

        output the vendor name in maximum 3 words or if not known than unknown.
        3. Output Requirements
        You must return ONLY a single JSON object.
        No explanation. No extra text. No comments. No calculations shown. Just JSON.
        Each category must contain an array of arrays.
        Each inner array must follow this format:
        ["Vendor/Store Name", Amount (number, two decimals, no currency symbol), "Description", "Income/Expense/Investment"]
        Only include categories that actually appear in the receipt.
        """

        try:
            response = model.generate_content(prompt)
            cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
            parsed_data = json.loads(cleaned_text)
            
            # Transform to flat list for frontend editing
            flat_data = []
            if isinstance(parsed_data, dict):
                for category, items in parsed_data.items():
                    for item in items:
                        # item format: ["Vendor", Amount, "Desc", "Type"]
                        if isinstance(item, list):
                            flat_data.append({
                                'category': category,
                                'vendor': item[0] if len(item) > 0 else 'Unknown',
                                'amount': item[1] if len(item) > 1 else 0,
                                'description': item[2] if len(item) > 2 else '',
                                'type': item[3] if len(item) > 3 else 'EXPENSE'
                            })
            
            return JsonResponse({'status': 'success', 'data': flat_data})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
@csrf_exempt
def process_image_input(request):
    """Sends image to Gemini and returns parsed JSON"""
    if request.method == "POST" and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            
            # Read image data
            image_data = image_file.read()
            
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            prompt = """
            You are an expert AI Transaction Categorizer. Analyze the receipt image for Vendor, items, and Total.

            **Rules:**
            1. **Categories (Exact List):** [Housing, Utilities, Food, Transportation, Healthcare, Personal Care, Entertainment, Clothing & Apparel, Groceries, Tax, Salary, Investment, Savings, Other].
            2. **Output Detail:** Capture: `[ "Vendor Name", Amount (N.NN), "Item Description", "Transaction Type(Income/Expense/Investment)" ]`. Use "Expense" for receipts.
            3. **Reconciliation (Mandatory):** Sum of ALL item amounts (including Tax/Fees under 'Other') MUST equal the receipt Total. Adjust if needed. The vendor name should be of maximum 3 words 
            4. **Omission:** Omit categories with $0.00 total.

            **Output Format (Strict JSON):**
            * Return **ONE JSON object**. Keys are exact Category Names. Values are arrays of item detail arrays.

            **Example:**
            ```json
            {
             "Food": [
              ["Dmart", 45.00, "Brown Bread", "Expense"],
              ["Dmart", 64.00, "Milk", "Expense"]
             ],
             "Other": [
              ["Dmart", 5.50, "Tax", "Expense"]
             ]
            }
            it should strictly return the json data only and nothing else)
            """
            
            # Create the image part for Gemini
            image_part = {
                "mime_type": image_file.content_type,
                "data": image_data
            }

            response = model.generate_content([prompt, image_part])
            cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
            parsed_data = json.loads(cleaned_text)
            
            # Transform to flat list for frontend editing (reusing same format as voice)
            flat_data = []
            if isinstance(parsed_data, dict):
                for category, items in parsed_data.items():
                    for item in items:
                        # item format: ["Vendor", Amount, "Desc", "Type"]
                        if isinstance(item, list):
                            flat_data.append({
                                'category': category,
                                'vendor': item[0] if len(item) > 0 else 'Unknown',
                                'amount': item[1] if len(item) > 1 else 0,
                                'description': item[2] if len(item) > 2 else '',
                                'type': item[3] if len(item) > 3 else 'EXPENSE'
                            })
            
            return JsonResponse({'status': 'success', 'data': flat_data})
        except Exception as e:
            print(f"Error processing image: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request or no image provided'})

# --- 3. UPDATED SAVE CONFIRMED (With Balance Check) ---
@login_required
@csrf_exempt
def save_confirmed_transactions(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body)
            items_list = payload.get('data', [])
            input_source = payload.get('source', 'VOICE')
            is_external = payload.get('is_external', False) # New Flag
            
            # 1. Calculate Total New Expense
            total_new_expense = sum(float(item.get('amount', 0)) for item in items_list if item.get('type') in ['EXPENSE', 'INVESTMENT'])
            
            # 2. Check Wallet Balance (ONLY if not external)
            if not is_external:
                # 1. Get Initial Balance from Profile
                try:
                    initial_balance = request.user.profile.cash_balance or Decimal(0)
                except Exception:
                    initial_balance = Decimal(0)

                incomes = Transaction.objects.filter(user=request.user, transaction_type='INCOME', is_external=False).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
                expenses = Transaction.objects.filter(user=request.user, transaction_type__in=['EXPENSE', 'INVESTMENT'], is_external=False).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
                
                current_balance = initial_balance + incomes - expenses

                if Decimal(total_new_expense) > current_balance:
                    return JsonResponse({'status': 'error', 'message': f'Insufficient Funds! Wallet Balance: ₹{current_balance}'})

            # 3. Save Data
            grouped_data = {}
            for item in items_list:
                cat = item.get('category', 'Other')
                if cat not in grouped_data: grouped_data[cat] = []
                grouped_data[cat].append(item)

            for category, items in grouped_data.items():
                total_amount = 0
                vendors = set()
                descriptions = []
                trans_type = "EXPENSE"
                
                for item in items:
                    vendor = item.get('vendor', 'Unknown')
                    amount = float(item.get('amount', 0))
                    desc = item.get('description', '')
                    t_type = item.get('type', 'EXPENSE').upper() 
                    
                    if category.lower() in ['savings', 'investment']:
                        t_type = 'INVESTMENT'

                    total_amount += amount
                    vendors.add(vendor)
                    descriptions.append(desc)
                    trans_type = t_type 

                merged_vendor = ", ".join(list(vendors))[:95]
                merged_desc = ", ".join(descriptions)[:250]

                Transaction.objects.create(
                    user=request.user,
                    amount=total_amount,
                    category=category,
                    vendor_name=merged_vendor,
                    description=merged_desc,
                    transaction_type=trans_type,
                    input_source=input_source,
                    is_external=is_external 
                )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})