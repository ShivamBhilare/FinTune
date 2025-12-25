import json
import math
import random
import traceback
from datetime import datetime
from decimal import Decimal

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

# Corrected Imports: Use ..models instead of dashboard.models
from ..models import FinancialGoal, Transaction

# --- Helper Functions ---

def get_financial_insights(user):
    """
    Calculates avg monthly savings (last 3 months) and highest spending category (current month).
    """
    now = timezone.now()
    total_surplus = 0
    months_analyzed = 3

    for i in range(months_analyzed):
        # Calculate target month and year accurately
        target_date = now - timezone.timedelta(days=30 * i)
        month = target_date.month
        year = target_date.year

        inc = Transaction.objects.filter(
            user=user, transaction_type='INCOME', date__month=month, date__year=year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        exp = Transaction.objects.filter(
            user=user, transaction_type='EXPENSE', date__month=month, date__year=year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_surplus += (inc - exp)
        
    avg_surplus = total_surplus / months_analyzed
    
    # Top Expense Category (Current Month)
    top_category = Transaction.objects.filter(
        user=user, 
        transaction_type='EXPENSE', 
        date__month=now.month, 
        date__year=now.year
    ).values('category').annotate(total=Sum('amount')).order_by('-total').first()
    
    top_spend = {
        'category': top_category['category'] if top_category else 'None',
        'amount': float(top_category['total']) if top_category else 0
    }
    
    return {
        'avg_surplus': max(0, round(float(avg_surplus), 0)),
        'top_spend': top_spend
    }

def safe_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == '' or str(val).lower() == 'null':
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

# --- View Functions ---

@login_required
def goal_tracker_view(request):
    """Renders the main Goal Simulator & Tracker page."""
    user = request.user
    goals = FinancialGoal.objects.filter(user=user).order_by('-created_at')
    insights = get_financial_insights(user)

    context = {
        'goals': goals,
        'insights': insights,
        'default_contribution': insights['avg_surplus'] # Pre-fill based on history
    }
    return render(request, 'goal_path.html', context)

@login_required
@csrf_exempt
def save_goal(request):
    """Saves a simulated goal to the database via AJAX."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if not data.get('name') or not data.get('target_amount'):
                return JsonResponse({'success': False, 'error': 'Missing required fields'})

            FinancialGoal.objects.create(
                user=request.user,
                name=data['name'],
                target_amount=data['target_amount'],
                current_amount=data.get('current_amount', 0),
                monthly_contribution=data['monthly_contribution'],
                target_date=data['target_date'],
                risk_profile='MEDIUM'
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

@login_required
def delete_goal(request, pk):
    """Deletes a specific goal and redirects back to tracker tab."""
    if request.method == 'POST':
        goal = FinancialGoal.objects.filter(pk=pk, user=request.user).first()
        if goal:
            goal.delete()
    return redirect(reverse('dashboard:goal_tracker') + '?tab=tracker')

@login_required
def calculate_goal_projection(request):
    """
    Advanced Monte Carlo Simulation:
    - Normal Distribution of returns
    - Annual Contribution Step-Up
    - Real-value adjustment (Inflation)
    """
    try:
        target_amount = safe_float(request.GET.get('target_amount'), 1000000)
        current_savings = safe_float(request.GET.get('current_savings'), 0)
        monthly_contribution = safe_float(request.GET.get('monthly_contribution'), 5000)
        step_up_pct = safe_float(request.GET.get('step_up_percentage'), 0) / 100
        
        # Date Logic
        target_date_str = request.GET.get('target_date')
        months_to_simulate = 60 # Default
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
                now = datetime.now()
                months_to_simulate = (target_date.year - now.year) * 12 + (target_date.month - now.month)
                months_to_simulate = max(1, months_to_simulate)
            except ValueError:
                pass

        # Simulation Constants
        SIMULATIONS = 1000
        annual_return, annual_volatility, inflation = 0.10, 0.12, 0.06
        
        monthly_ret = annual_return / 12
        monthly_vol = annual_volatility / math.sqrt(12)
        monthly_inf = inflation / 12

        # results[sim_index][month_index]
        all_paths = []
        
        for _ in range(SIMULATIONS):
            path = [current_savings]
            balance = current_savings
            current_monthly_contrib = monthly_contribution
            
            for m in range(1, months_to_simulate + 1):
                # Annual Step-Up
                if m > 1 and (m - 1) % 12 == 0:
                    current_monthly_contrib *= (1 + step_up_pct)
                
                # Market Motion (Stochastic)
                r = random.gauss(monthly_ret, monthly_vol)
                r_real = r - monthly_inf # Real return adjustment
                
                balance = balance * (1 + r_real) + current_monthly_contrib
                path.append(balance)
            
            all_paths.append(path)

        # Aggregate Percentiles for Charting
        chart_data = {'labels': list(range(months_to_simulate + 1)), 'pessimistic': [], 'median': [], 'optimistic': []}
        
        for m in range(months_to_simulate + 1):
            # Extract balance of all simulations at month 'm'
            slice_at_m = sorted([sim[m] for sim in all_paths])
            chart_data['pessimistic'].append(round(slice_at_m[int(SIMULATIONS * 0.1)], 2))
            chart_data['median'].append(round(slice_at_m[int(SIMULATIONS * 0.5)], 2))
            chart_data['optimistic'].append(round(slice_at_m[int(SIMULATIONS * 0.9)], 2))

        final_balances = [sim[-1] for sim in all_paths]
        success_prob = (sum(1 for b in final_balances if b >= target_amount) / SIMULATIONS) * 100

        return JsonResponse({
            'success': True,
            'success_probability': round(success_prob, 1),
            'chart_data': chart_data,
            'months': months_to_simulate
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
