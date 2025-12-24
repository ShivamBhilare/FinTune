import google.generativeai as genai
from django.conf import settings
from django.utils import timezone
from .models import Transaction
import json
import logging

logger = logging.getLogger(__name__)

import google.generativeai as genai
from django.conf import settings
from django.utils import timezone
from .models import Transaction
import json
import logging

logger = logging.getLogger(__name__)

# Import existing pattern engines
from .utils import get_recurring_stats, get_financial_persona, get_most_active_day
from .views.budgetGen_views import get_monthly_data

def generate_personalized_quests(user):
    """
    Generates 3 personalized quests using Privacy-First Context.
    Uses local pattern detection (Persona, Recurring, Budget) and sends only high-level info to Gemini.
    """
    try:
        # 1. Gather Local Context (Privacy-Safe)
        persona_data = get_financial_persona(user)
        persona_name = persona_data.get('persona', 'The Balanced Spender')
        
        recurring_list, total_recurring = get_recurring_stats(user)
        recurring_count = len(recurring_list)
        
        most_active_day = get_most_active_day(user)
        
        # Budget Data
        # get_monthly_data returns: income, spent_needs, spent_wants, saved_savings
        try:
            income, spent_needs, spent_wants, saved_savings = get_monthly_data(user)
            # Calculate percentages for context
            needs_pct = int((spent_needs / income * 100)) if income > 0 else 0
            wants_pct = int((spent_wants / income * 100)) if income > 0 else 0
        except Exception:
            needs_pct = 50
            wants_pct = 30 # Default/Fallback

        # Extract explicit Top Category for more context
        top_cat = "General"
        try:
             # get_financial_persona computes this internally, but we can re-derive or blindly trust the 'icon' inference
             # For better accuracy, let's peek at the Transaction data quickly or use what we have.
             # Actually, let's use the persona mapping we know.
             pass 
        except:
             pass

        # 2. Construct Privacy-Preserving Prompt (Variable Streak Challenge)
        prompt = f"""
        Role: Gamification Engine for FinTune.
        User Context:
        - Persona: "{persona_name}"
        - Top Spending Habit: Analyze {most_active_day} trends.
        - Recurring Bills: {recurring_count} identified.
        
        Task: Generate ONE Personalized Streak Challenge to break a spending habit.
        
        The goal is to challenge the user to STOP spending on their most problematic category or vendor for a set number of days.
        
        Rules:
        1. Look at their Persona/Habits. 
           - If "The Foodie", challenge: "No Outside Food for 5 Days" (Category: Food).
           - If "The Trendsetter" or "The Shopper", challenge: "No New Clothes" (Category: Clothing & Apparel).
           - If they have many recurring bills, challenge: "No New Subscriptions" (Category: Utilities or Entertainment).
        2. Assign a 'duration_days' (Integer 1-30) based on difficulty.
           - Hardier habits = shorter duration first.
           - General savings = longer duration.
        3. Title must be catchy/fun.
        4. CRITICAL: For 'NO_SPEND_CATEGORY', you MUST use one of the EXACT categories from this list:
           ['Housing', 'Utilities', 'Food', 'Transportation', 'Healthcare', 'Personal Care', 'Entertainment', 'Clothing & Apparel', 'Groceries', 'Tax', 'Other'].
           Do NOT use generic terms like "Shopping" or "Dining". Use the closest match from the list.
        
        Output JSON Object (Single Item):
        {{
            "title": "Starbucks Fast",
            "description": "Save $20 by making coffee at home.",
            "type": "NO_SPEND_CATEGORY", 
            "target_variable": {{"target_category": "Food"}}, 
            "duration_days": 3,
            "reward_points": 300,
            "reward_xp": 100,
            "difficulty": "Rare"
        }}
        
        Valid Types: 'NO_SPEND_CATEGORY', 'NO_SPEND_VENDOR', 'SAVE_AMOUNT'.
        """

        # 3. Call Gemini
        if not settings.GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY not set. Using fallback.")
            raise Exception("No API Key")

        # Debug: Print first few chars of key to confirm it's loaded
        key_suffix = settings.GOOGLE_API_KEY[:4] + "..." if settings.GOOGLE_API_KEY else "None"
        print(f"DEBUG: Using Google API Key starting with: {key_suffix}")
            
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # Swithced to 1.5-flash for better free tier quota
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        
        challenge = json.loads(text)
        
        # Ensure it's a list for compatibility or handle single object (we want single now)
        # Ensure it's a list for compatibility or handle single object (we want single now)
        if isinstance(challenge, list):
            challenge = challenge[0]
            
        # --- SANITIZATION STEP ---
        # AI often hallucinates categories like "Shopping" or "Dining". We must map them to valid DB choices.
        valid_categories = [c[0] for c in Transaction.CATEGORIES]
        target_var = challenge.get('target_variable', {})
        t_cat = target_var.get('target_category')
        
        if t_cat:
            # 1. Direct Match?
            if t_cat in valid_categories:
                pass # Good
            else:
                # 2. Map known hallucinations
                print(f"DEBUG: AI generated invalid category: '{t_cat}'. Attempting fix...")
                if t_cat in ['Shopping', 'Retail', 'Clothes']: 
                    target_var['target_category'] = 'Clothing & Apparel'
                elif t_cat in ['Dining', 'Restaurants', 'Eating Out']:
                    target_var['target_category'] = 'Food'
                elif t_cat in ['Gas', 'Fuel']:
                    target_var['target_category'] = 'Transportation'
                else:
                    # 3. Fallback: Check for partial case-insensitive match
                    found = False
                    for valid in valid_categories:
                        if valid.lower() == t_cat.lower():
                            target_var['target_category'] = valid
                            found = True
                            break
                    if not found:
                        # 4. Final Fallback
                        print(f"DEBUG: Could not map '{t_cat}'. Defaulting to 'Other'.")
                        target_var['target_category'] = 'Other'
            
            # Save back
            challenge['target_variable'] = target_var
            # --- END SANITIZATION ---
            
        return [challenge] # Return as list to match expectation of view/iterator logic temporarily


    except Exception as e:
        logger.error(f"Error generating AI quests: {e}")
        # Fallback quests if AI fails
        return [
            { 
                'title': 'The 3-Day Saver', 'description': 'Save at least ₹500/day for 3 days.', 
                'difficulty': 'Common', 'reward_points': 300, 'reward_xp': 150,
                'type': 'SAVE_AMOUNT', 'target_variable': {'amount': 500}, 'duration_days': 3
            }
        ]
