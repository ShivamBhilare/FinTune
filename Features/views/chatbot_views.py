from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
import json
import logging
import google.generativeai as genai

# Correct relative import for models since we are in Features/views/
from ..models import Transaction, FinancialGoal, ChatMessage

logger = logging.getLogger(__name__)

def get_chat_response(user, user_message, history=None):
    """
    Generates a response from the AI Chatbot (CFO) based on user's financial context and chat history.
    """
    try:
        # 1. Gather Context (Privacy-First)
        
        # --- CORRECT BALANCE LOGIC FROM DASHBOARD ---
        try:
            initial_balance = 0
            if hasattr(user, 'profile'):
                 initial_balance = user.profile.cash_balance or 0
        except:
            initial_balance = 0

        # Exclude external transactions from Wallet Balance
        income = Transaction.objects.filter(user=user, transaction_type='INCOME', is_external=False).aggregate(Sum('amount'))['amount__sum'] or 0
        # Include INVESTMENT in expenses for balance calculation
        expense = Transaction.objects.filter(user=user, transaction_type__in=['EXPENSE', 'INVESTMENT'], is_external=False).aggregate(Sum('amount'))['amount__sum'] or 0
        balance = initial_balance + income - expense
        # ---------------------------------------------

        # Total Investments (for context)
        investments = Transaction.objects.filter(user=user, transaction_type='INVESTMENT').aggregate(Sum('amount'))['amount__sum'] or 0

        # Recent Transactions (Last 5)
        recent_txs = Transaction.objects.filter(user=user).order_by('-date')[:5]
        recent_txs_str = "\n".join([f"- {t.date.strftime('%Y-%m-%d')}: {t.vendor_name} ({t.category}) - {t.amount} ({t.transaction_type})" for t in recent_txs])

        # Goals
        goals = FinancialGoal.objects.filter(user=user)
        goals_str = "\n".join([f"- {g.name}: {g.current_amount}/{g.target_amount} (Risk: {g.risk_profile})" for g in goals])

        # Format History
        history_str = ""
        if history:
            history_str = "Previous Conversation:\n" + "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

        # 2. Construct Prompt
        prompt = f"""
        Role: You are FinTune's AI CFO, a smart, friendly, and encouraging personal finance assistant.
        
        User Context:
        - Name: {user.first_name}
        - Current Wallet Balance: {balance}
        - Total Income (Internal): {income}
        - Total Expenses (Internal): {expense}
        - Total Investments: {investments}
        
        Recent Activity:
        {recent_txs_str}
        
        Financial Goals:
        {goals_str}
        
        {history_str}
        
        User Query: "{user_message}"
        
        Instructions:
        - Answer the user's query using the provided context and previous conversation.
        - Give more humanized, conversational, and empathetic answers. Avoid sounding robotic.
        - Be concise (max 3-4 sentences unless detailed analysis is asked).
        - If the user asks about their spending, use the recent activity data.
        - If the user asks for advice, give specific, actionable tips based on their goals and balance.
        - Tone: Professional yet approachable, motivating.
        - Do NOT invent data. If you don't know, say "I don't have that information right now."
        - Format: Use simple text, you can use markdown for bolding key figures.
        """

        # 3. Call Gemini
        if not settings.GOOGLE_API_KEY:
            return "I'm sorry, my brain (API Key) is missing. Please check the settings."

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        logger.error(f"Error in AI Chatbot: {e}")
        import traceback
        traceback.print_exc()
        return f"I'm having a bit of trouble connecting to my financial brain right now. Error details: {str(e)}"


@csrf_exempt
@login_required
def chat_api(request):
    """
    API View to handle chat messages.
    Expects POST with 'message'. Returns JSON {'response': '...'}.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': 'Empty message'}, status=400)
            
            # 1. Save User Message
            ChatMessage.objects.create(
                user=request.user,
                role='user',
                content=user_message
            )
            
            # 2. Fetch History (Last 10 messages)
            recent_history = ChatMessage.objects.filter(user=request.user).order_by('-timestamp')[:10]
            history_list = [{'role': msg.role, 'content': msg.content} for msg in reversed(recent_history)]
            
            # 3. Get AI Response
            ai_reply = get_chat_response(request.user, user_message, history=history_list)
            
            # 4. Save AI Response
            ChatMessage.objects.create(
                user=request.user,
                role='ai',
                content=ai_reply
            )
            
            return JsonResponse({'response': ai_reply})
            
        except Exception as e:
            logger.error(f"Chat API Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'POST required'}, status=405)
