import google.generativeai as genai
from django.conf import settings
from django.utils import timezone
from .models import Transaction
import json
import logging

logger = logging.getLogger(__name__)

from .utils import get_recurring_stats

def generate_personalized_quests(user):
    """
    Generates 3 personalized quests for the user based on their transaction history.
    Returns a list of dictionaries.
    """
    try:
        # 1. Fetch recent history for context
        recent_txns = Transaction.objects.filter(user=user).order_by('-date')[:20]
        history_text = "\n".join([f"- {t.date.date()}: {t.vendor_name} ({t.category}) - {t.amount}" for t in recent_txns])
        
        if not history_text:
            history_text = "No recent transactions. Generate generic financial wisdom quests."

        # 1b. Fetch Recurring Stats for Context (Smart AI)
        recurring_list, total_recurring = get_recurring_stats(user)
        recurring_text = f"User has approx ₹{total_recurring} in fixed monthly recurring expenses."
        if recurring_list:
             recurring_text += " Known recurring vendors: " + ", ".join([r['vendor'] for r in recurring_list[:5]])

        # 2. Construct Prompt
        prompt = f"""
        You are a Gamification Engine for a Personal Finance App. 
        Analyze the user's recent transaction history to generate 3 personalized "Daily Quests" to help them save money or improve habits.

        User History:
        {history_text}
        
        Financial Context:
        {recurring_text}
        (CRITICAL: Do not generate 'Spend Less' targets that conflict with these fixed obligations or are impossible. e.g. Do not ask for 0 spend if they have high daily fixed costs.)
        
        Generate exactly 3 diverse quests in strict JSON format. 
        Each quest must have:
        - id: unique string (e.g. 'quest_1')
        - title: Fun RPG-style title
        - description: Short description of the task (e.g. "Save 500Rs today")
        - rarity: 'Common', 'Rare', or 'Epic'
        - rewardXP: Integer (50-200)
        - rewardCoins: Integer (100-500)
        - icon: FontAwesome class (e.g. 'fas fa-mug-hot')
        - type: One of ['SPEND_LESS_THAN', 'NO_SPEND', 'TRANSACTION_BEFORE', 'SAVE_AMOUNT']
        - target_category: The category to track (from: Housing, Utilities, Food, Transportation, Healthcare, Personal Care, Entertainment, Clothing & Apparel, Groceries, Tax, Investment, Savings, Other). Or null if not applicable.
        - target_amount: Numeric threshold (e.g. 500). Required for SPEND_LESS_THAN and SAVE_AMOUNT.
        - target_time: Hour (0-23) for time-based quests. Or null.

        Output ONLY valid JSON list. No markdown.
        """

        # 3. Call Gemini
        # 3. Call Gemini
        if not settings.GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY not set. Using fallback.")
            raise Exception("No API Key") # Trigger fallback
            
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        
        quests = json.loads(text)
        
        # Ensure IDs are unique-ish
        import uuid
        for q in quests:
            q['id'] = f"ai_{uuid.uuid4().hex[:8]}"
            
        return quests

    except Exception as e:
        logger.error(f"Error generating AI quests: {e}")
        # Fallback quests if AI fails
        return [
            { 
                'id': 'fallback_1', 'title': 'The Saver', 'description': 'Save at least ₹500 today.', 'rarity': 'Common', 
                'rewardXP': 50, 'rewardCoins': 100, 'icon': 'fas fa-piggy-bank',
                'type': 'SAVE_AMOUNT', 'target_category': 'Savings', 'target_amount': 500 
            },
            { 
                'id': 'fallback_2', 'title': 'Coffee Break', 'description': 'Skip the cafe today (Spend 0 on Food).', 'rarity': 'Rare', 
                'rewardXP': 100, 'rewardCoins': 200, 'icon': 'fas fa-mug-hot',
                'type': 'NO_SPEND', 'target_category': 'Food', 'target_amount': 0 
            },
            { 
                'id': 'fallback_3', 'title': 'Early Bird', 'description': 'Log a transaction before 10 AM.', 'rarity': 'Uncommon', 
                'rewardXP': 75, 'rewardCoins': 150, 'icon': 'fas fa-sun',
                'type': 'TRANSACTION_BEFORE', 'target_category': None, 'target_amount': 0, 'target_time': 10
            }
        ]
