from flask import Blueprint, jsonify
from models import db, Income, Expense, MonthlyIncome, Budget, Account
from routes.auth import token_required
from sqlalchemy import func
from datetime import datetime, timedelta

forecasts_bp = Blueprint('forecasts', __name__, url_prefix='/api/forecast')

@forecasts_bp.route('', methods=['GET'])
@token_required
def get_forecast(current_user_id):
    """
    Project future financial standing based on Account balances and historical data
    """
    today = datetime.utcnow().date()
    
    # 1. Calculate Current Balance (Sum of Account Balances)
    total_balance = db.session.query(func.sum(Account.balance)).filter_by(user_id=current_user_id).scalar()
    current_balance = float(total_balance) if total_balance else 0.0

    # 2. Daily Burn Rate (last 60 days) - Smooth Average
    sixty_days_ago = today - timedelta(days=60)
    expenses_60 = float(db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user_id,
        Expense.date >= sixty_days_ago
    ).scalar() or 0)
    daily_burn = expenses_60 / 60.0

    # 3. Analyze Income for Paydays (60 days history)
    incomes = Income.query.filter(
        Income.user_id == current_user_id,
        Income.date >= sixty_days_ago
    ).all()

    # Strategy: Find recurring paydays
    # Group by amount (fuzzy match) or day? 
    # Simpler: Just group by day of month (1-31) and average the amount.
    # Any income > $100 is considered a "payday". Smaller stuff is smoothed.
    
    paydays = {} # { day_of_month: avg_amount }
    payday_counts = {} # { day_of_month: count }
    small_income_sum = 0
    
    for inc in incomes:
        amt = float(inc.amount)
        if amt > 100:
            dom = inc.date.day
            if dom not in paydays:
                paydays[dom] = 0
                payday_counts[dom] = 0
            paydays[dom] += amt
            payday_counts[dom] += 1
        else:
            small_income_sum += amt
            
    # Calculate averages for paydays
    final_paydays = {}
    for dom in paydays:
        # Only count as separate payday if it happened at least once in 60 days (it did, obviously)
        # We assume it repeats monthly.
        avg_amt = paydays[dom] / payday_counts[dom]
        final_paydays[dom] = avg_amt
        
    daily_small_income = small_income_sum / 60.0

    # 4. Correct for Budget (current month remaining)
    month_str = today.strftime('%Y-%m')
    budgets = Budget.query.filter_by(user_id=current_user_id, month=month_str).all()
    total_budget = sum(float(b.amount) for b in budgets)
    month_start = today.replace(day=1)
    spent_this_month = float(db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user_id,
        Expense.date >= month_start
    ).scalar() or 0)
    remaining_budget = max(0, total_budget - spent_this_month)

    # 5. Projection logic (90 days)
    projection = []
    temp_balance = current_balance
    
    # Spread remaining budget over the rest of THIS month
    days_in_current_month_total = (month_start + timedelta(days=32)).replace(day=1) - month_start
    days_left_in_month = max((month_start + days_in_current_month_total - today).days, 1)
    extra_daily_expense_for_month = remaining_budget / days_left_in_month
    
    total_projected_income_90d = 0

    for i in range(91):
        target_date = today + timedelta(days=i)
        
        # Apply burn rate
        current_daily_expense = daily_burn
        
        # If still in current month, add the "budget catchup" expense
        if i < days_left_in_month:
            current_daily_expense += extra_daily_expense_for_month
            
        temp_balance -= current_daily_expense
        
        # Apply Income
        # 1. Smooth small income
        temp_balance += daily_small_income
        total_projected_income_90d += daily_small_income
        
        # 2. Discrete Paydays
        if target_date.day in final_paydays:
            temp_balance += final_paydays[target_date.day]
            total_projected_income_90d += final_paydays[target_date.day]
            
        projection.append({
            'date': target_date.isoformat(),
            'balance': round(temp_balance, 2)
        })

    # Average daily income for the summary stats
    avg_daily_income = total_projected_income_90d / 90.0

    return jsonify({
        'current_balance': round(current_balance, 2),
        'daily_burn': round(daily_burn, 2),
        'daily_income': round(avg_daily_income, 2), 
        'projection': projection
    }), 200
