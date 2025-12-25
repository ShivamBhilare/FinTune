from decimal import Decimal

def get_health_score_context(user):
    # 1. Data Aggregation
    # Handle cases where monthly_income might be None
    income = Decimal(user.profile.monthly_income or 0)
    
    # Add any 'INCOME' category transactions to base profile income
    extra_income = sum(t.amount for t in user.transactions.filter(transaction_type='INCOME'))
    total_income = income + extra_income

    expenses = sum(t.amount for t in user.transactions.filter(transaction_type='EXPENSE'))
    investments = sum(t.amount for t in user.transactions.filter(transaction_type='INVESTMENT'))
    # Using 'DEBT_PAYMENT' as added to the model
    liabilities = sum(t.amount for t in user.transactions.filter(transaction_type='DEBT_PAYMENT'))

    if total_income <= 0:
        return {'health_score': 0, 'message': "Add income to see your score!", 'score_color': 'text-red-500', 'progress_color': 'bg-red-500', 'ratios': {'expense': 0, 'investment': 0, 'debt': 0}}

    # 2. Ratio Calculations
    exp_ratio = (expenses / total_income) * 100
    inv_ratio = (investments / total_income) * 100
    debt_ratio = (liabilities / total_income) * 100

    # 3. Scoring Algorithm
    
    # A. Expense Score (30 pts) - Goal < 40%
    if exp_ratio <= 40:
        score_exp = 30
    else:
        # Decays from 30 to 0 between 40% and 100% spending
        score_exp = max(0, 30 - ((exp_ratio - 40) * 0.5))

    # B. Investment Score (30 pts) - Goal > 20%
    score_inv = min(30, (inv_ratio / 20) * 30)

    # C. Debt Ratio Score (20 pts) - Goal < 30%
    if debt_ratio <= 30:
        score_debt = 20
    else:
        # Sharp decay if debt exceeds 30% of income
        score_debt = max(0, 20 - ((debt_ratio - 30) * 1.0))

    # D. Cash Flow Score (20 pts)
    # Net Flow = Income - (Expenses + Investments + Liabilities)
    net_flow = total_income - (expenses + investments + liabilities)
    score_flow = 20 if net_flow > 0 else 0

    # 4. Final Aggregation
    total_score = round(score_exp + score_inv + score_debt + score_flow)

    # 5. Visual Feedback Logic
    if total_score >= 80:
        color, p_color, msg = 'text-emerald-400', 'bg-emerald-500', "Financial Rockstar! Your habits are sustainable."
    elif total_score >= 60:
        color, p_color, msg = 'text-yellow-400', 'bg-yellow-500', "On the right track. Try reducing debt or expenses."
    else:
        color, p_color, msg = 'text-red-500', 'bg-red-600', "Caution: High burn rate or debt detected."

    return {
        'health_score': total_score,
        'score_color': color,
        'progress_color': p_color,
        'message': msg,
        'ratios': {
            'expense': round(exp_ratio),
            'investment': round(inv_ratio),
            'debt': round(debt_ratio)
        }
    }
