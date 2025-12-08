from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from dashboard.models import FinancialGoal
from dashboard.views.budgetGen_views import get_monthly_data
from datetime import datetime
import math
import random
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
import json

from django.db.models import Sum
from dashboard.models import Transaction, FinancialGoal
# ... (existing imports)

def get_financial_insights(user):
    """
    Calculates avg monthly savings (last 3 months) and highest spending category (last month).
    """
    now = datetime.now()
    # 1. Avg Savings (Surplus) over last 3 months
    total_income = 0
    total_expenses = 0
    
    # Simple loop for last 3 months
    for i in range(3):
        month = now.month - i
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        
        inc = Transaction.objects.filter(
            user=user, transaction_type='INCOME', date__month=month, date__year=year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        exp = Transaction.objects.filter(
            user=user, transaction_type='EXPENSE', date__month=month, date__year=year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_income += inc
        total_expenses += exp
        
    avg_surplus = (total_income - total_expenses) / 3
    avg_surplus = float(avg_surplus) if avg_surplus > 0 else 0

    # 2. Top Expense Category (Last Month)
    top_category = Transaction.objects.filter(
        user=user, transaction_type='EXPENSE', date__month=now.month, date__year=now.year
    ).values('category').annotate(total=Sum('amount')).order_by('-total').first()
    
    top_spend = {
        'category': top_category['category'] if top_category else 'None',
        'amount': float(top_category['total']) if top_category else 0
    }
    
    return {
        'avg_surplus': round(avg_surplus, 0),
        'top_spend': top_spend
    }

@login_required
def goal_tracker_view(request):
    """
    Renders the main Goal Simulator & Tracker page.
    """
    user = request.user
    goals = FinancialGoal.objects.filter(user=user).order_by('-created_at')

    # Get Insights (Real Data)
    insights = get_financial_insights(user)

    context = {
        'goals': goals,
        'insights': insights, # Pass to template
        'default_contribution': 0
    }
    return render(request, 'dashboard/goal_simulator.html', context)

@login_required
@csrf_exempt
def save_goal(request):
    """
    Saves a simulated goal to the database.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Basic validation
            if not data.get('name') or not data.get('target_amount'):
                return JsonResponse({'success': False, 'error': 'Missing required fields'})

            FinancialGoal.objects.create(
                user=request.user,
                name=data['name'],
                target_amount=data['target_amount'],
                current_amount=data.get('current_amount', 0),
                monthly_contribution=data['monthly_contribution'],
                target_date=data['target_date'], # Expecting YYYY-MM-DD
                risk_profile=data.get('risk_profile', 'MEDIUM') # Default since UI removed it
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

from django.urls import reverse

@login_required
def delete_goal(request, pk):
    """
    Deletes a specific goal.
    """
    if request.method == 'POST':
        try:
            goal = FinancialGoal.objects.get(pk=pk, user=request.user)
            goal.delete()
        except FinancialGoal.DoesNotExist:
            pass 
    return redirect(reverse('dashboard:goal_tracker') + '?tab=tracker')

@login_required
def calculate_goal_projection(request):
    """
    API for Monte Carlo Simulation with Step-Up Logic.
    """
    try:
        # Helper for safe float conversion
        def safe_float(val, default=0.0):
            try:
                if val is None or val == '': return default
                return float(val)
            except (ValueError, TypeError):
                return default

        target_amount = safe_float(request.GET.get('target_amount'), 1000000)
        current_savings = safe_float(request.GET.get('current_savings'), 0)
        monthly_contribution = safe_float(request.GET.get('monthly_contribution'), 5000)
        step_up_percentage = safe_float(request.GET.get('step_up_percentage'), 0) # Annual % increase
        # risk_profile = request.GET.get('risk_profile', 'MEDIUM') - Removed
        
        target_date_str = request.GET.get('target_date')
        if target_date_str and target_date_str.lower() != 'null' and target_date_str != '':
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
                now = datetime.now()
                months_to_simulate = (target_date.year - now.year) * 12 + (target_date.month - now.month)
                months_to_simulate = max(1, months_to_simulate)
            except ValueError:
                months_to_simulate = 60
        else:
            months_to_simulate = 60 # Default 5 years

        # Simulation Parameters
        SIMULATIONS = 1000
        
        # Defaulting to MEDIUM Risk profile stats (10% Return, 12% Volatility)
        annual_return = 0.10
        annual_volatility = 0.12

        monthly_return = annual_return / 12
        monthly_volatility = annual_volatility / math.sqrt(12)
        inflation_monthly = 0.06 / 12 # 6% Inflation

        final_amounts = []
        all_paths = [[current_savings] * (months_to_simulate + 1) for _ in range(SIMULATIONS)]

        # Step-Up Preparation: Calculate multiplier per month? 
        # Actually steps up annually. 
        # Month 1-12: contribution
        # Month 13-24: contribution * (1 + step_up%)
        
        for sim in range(SIMULATIONS):
            balance = current_savings
            current_monthly_contribution = monthly_contribution
            
            for month in range(1, months_to_simulate + 1):
                # Annual Step-Up event
                if month > 1 and (month - 1) % 12 == 0:
                    current_monthly_contribution *= (1 + step_up_percentage / 100)
                
                # Market Motion
                r = random.gauss(monthly_return, monthly_volatility)
                
                # Inflation Adjustment logic (Real Value Simulation)
                # r_real ~= r_nominal - inflation
                r_sim = r - inflation_monthly
                
                # For Contribution: If we want Real Value, we assume contribution grows with inflation typically.
                # If we assume step-up is *on top of inflation* (Real Growth), we keep it as is.
                # If step-up is nominal (salary hike), we need to discount it.
                # Let's simplify: User inputs Nominal Step-Up. We discount it by inflation to get Real Contribution impact.
                # Real Contribution = Nominal Contribution / ((1+inf)^t)
                # This is complex to model "perfectly" without confusing the user.
                # Let's stick to the previous model: Asset returns are Real. 
                # Contribution: We assume the user increases it to match inflation NATURALLY, 
                # PLUS the step_up_percentage is "Real Growth" in contribution (promotion, etc).
                
                balance = balance * (1 + r_sim) + current_monthly_contribution
                
                val = all_paths[sim][month-1] * (1 + r_sim) + current_monthly_contribution
                all_paths[sim][month] = val

            final_amounts.append(all_paths[sim][-1])

        # Data aggregation
        chart_data = {
            'labels': list(range(months_to_simulate + 1)),
            'optimistic': [], 'median': [], 'pessimistic': []
        }
        
        for month in range(months_to_simulate + 1):
            values_at_month = sorted([all_paths[i][month] for i in range(SIMULATIONS)])
            chart_data['pessimistic'].append(values_at_month[int(SIMULATIONS * 0.10)])
            chart_data['median'].append(values_at_month[int(SIMULATIONS * 0.50)])
            chart_data['optimistic'].append(values_at_month[int(SIMULATIONS * 0.90)])

        success_count = sum(1 for amount in final_amounts if amount >= target_amount)
        success_prob = (success_count / SIMULATIONS) * 100

        return JsonResponse({
            'success_probability': round(success_prob, 1),
            'chart_data': chart_data,
            'months': months_to_simulate
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f"Simulation failed: {str(e)}"}, status=400)
