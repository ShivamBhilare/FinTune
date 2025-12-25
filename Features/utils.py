import google.generativeai as genai
import os
import json
import re
from django.conf import settings

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

def clean_json_string(json_string):
    """
    Cleans the JSON string returned by Gemini to ensure it's valid JSON.
    Removes standard markdown code blocks.
    """
    cleaned = re.sub(r'```json\s*', '', json_string)
    cleaned = re.sub(r'```\s*', '', cleaned)
    return cleaned.strip()

def process_voice_with_gemini(transcript):
    """
    Processes voice transcript using Gemini to extract transaction data.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
        You are an expert AI Transaction Categorizer. Your task is to analyze a text-based purchase receipt. The text will be generated from voice input (speech-to-text), and may contain small transcription errors. Your job is to accurately identify the vendor name, individual purchased items, and the price of each item.

        1. Input Format
        You will receive plain text containing: '{transcript}'
        
        2. Categorization Rules
        You must categorize each item into one of the following exact categories:
        [Housing, Utilities, Food, Transportation, Healthcare, Personal Care, Entertainment, Clothing & Apparel, Groceries, Tax, Salary, Investment, Savings, Liabilities,Other]
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
        cleaned_json = clean_json_string(response.text)
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"Error processing voice with Gemini: {e}")
        return {"error": str(e)}

def process_image_with_gemini(image_file):
    """
    Processes receipt image using Gemini Vision to extract transaction data.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """
            You are an expert AI Transaction Categorizer. Analyze the receipt image for Vendor, items, and Total.

            **Rules:**
            1. **Categories (Exact List):** [Housing, Utilities, Food, Transportation, Healthcare, Personal Care, Entertainment, Clothing & Apparel, Groceries, Tax, Salary, Investment, Savings, Liabilities,Other].
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
            
    try:
        # Load image data
        image_data = {
            'mime_type': image_file.content_type,
            'data': image_file.read()
        }
        
        response = model.generate_content([prompt, image_data])
        cleaned_json = clean_json_string(response.text)
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"Error processing image with Gemini: {e}")
        return {"error": str(e)}
