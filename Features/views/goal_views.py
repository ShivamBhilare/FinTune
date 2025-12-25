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
                year_idx = (m - 1) // 12
                current_monthly_contrib = monthly_contribution * ((1 + step_up_pct) ** year_idx)
                
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

# --- New Views for Modal ---

def _run_monte_carlo(current_savings, monthly_contribution, step_up_pct, months_to_simulate, target_amount):
    """Reusable MC Logic"""
    SIMULATIONS = 1000
    annual_return, annual_volatility, inflation = 0.10, 0.12, 0.06
    
    monthly_ret = annual_return / 12
    monthly_vol = annual_volatility / math.sqrt(12)
    monthly_inf = inflation / 12

    all_paths = []
    
    for _ in range(SIMULATIONS):
        path = [current_savings]
        balance = current_savings
        current_monthly_contrib = monthly_contribution
        
        for m in range(1, months_to_simulate + 1):
            # Yearly Step-Up (State-less calculation)
            year_idx = (m - 1) // 12
            current_monthly_contrib = monthly_contribution * ((1 + step_up_pct) ** year_idx)
            
            r = random.gauss(monthly_ret, monthly_vol)
            r_real = r - monthly_inf
            
            balance = balance * (1 + r_real) + current_monthly_contrib
            path.append(balance)
        
        all_paths.append(path)

    chart_data = {'labels': list(range(months_to_simulate + 1)), 'pessimistic': [], 'median': [], 'optimistic': []}
    
    for m in range(months_to_simulate + 1):
        slice_at_m = sorted([sim[m] for sim in all_paths])
        chart_data['pessimistic'].append(round(slice_at_m[int(SIMULATIONS * 0.1)], 2))
        chart_data['median'].append(round(slice_at_m[int(SIMULATIONS * 0.5)], 2))
        chart_data['optimistic'].append(round(slice_at_m[int(SIMULATIONS * 0.9)], 2))

    final_balances = [sim[-1] for sim in all_paths]
    success_prob = (sum(1 for b in final_balances if b >= target_amount) / SIMULATIONS) * 100
    
    return chart_data, success_prob

from django.shortcuts import get_object_or_404

@login_required
def get_goal_details(request, pk):
    goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
    
    # Calculate months remaining
    today = timezone.now().date()
    
    # More robust calculation considering days
    diff = (goal.target_date.year - today.year) * 12 + (goal.target_date.month - today.month)
    
    # If target date is in future but same month, assume 1 month
    if diff <= 0 and goal.target_date > today:
        diff = 1
    
    months_remaining = max(1, diff)
    
    # Format Duration String
    years = months_remaining // 12
    extra_months = months_remaining % 12
    
    duration_str = ""
    if years > 0:
        duration_str += f"{years} Year{'s' if years != 1 else ''}"
    if extra_months > 0:
        if duration_str:
            duration_str += ", "
        duration_str += f"{extra_months} Month{'s' if extra_months != 1 else ''}"
        
    if not duration_str:
        duration_str = "< 1 Month"
    
    # Run Simulation for this specific goal
    # Assuming standard 10% step up since it's not in DB yet
    step_up_pct = 0.10 
    
    chart_data, success_prob = _run_monte_carlo(
        float(goal.current_amount),
        float(goal.monthly_contribution),
        step_up_pct,
        months_remaining,
        float(goal.target_amount)
    )
    
    return JsonResponse({
        'success': True,
        'goal': {
            'id': goal.id,
            'name': goal.name,
            'target_amount': goal.target_amount,
            'current_amount': goal.current_amount,
            'monthly_contribution': goal.monthly_contribution,
            'target_date': goal.target_date,
            'months_remaining': months_remaining,
            'duration_left': duration_str
        },
        'chart_data': chart_data,
        'success_probability': round(success_prob, 1)
    })

@login_required
@csrf_exempt
def update_goal_balance(request, pk):
    if request.method == 'POST':
        try:
            goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
            data = json.loads(request.body)
            
            action = data.get('action') # 'add' or 'remove'
            amount = Decimal(str(data.get('amount', 0)))
            
            if amount < 0:
                return JsonResponse({'success': False, 'error': 'Amount must be positive'})

            if action == 'add':
                goal.current_amount += amount
            elif action == 'remove':
                if goal.current_amount < amount:
                    return JsonResponse({'success': False, 'error': 'Insufficient funds in goal'})
                goal.current_amount -= amount
            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'})
                
            goal.save()
            return JsonResponse({'success': True, 'new_amount': goal.current_amount})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
