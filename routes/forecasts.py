from flask import Blueprint, jsonify
from models import db, Income, Expense, MonthlyIncome, Budget
from routes.auth import token_required
from sqlalchemy import func
from datetime import datetime, timedelta

forecasts_bp = Blueprint('forecasts', __name__, url_prefix='/api/forecast')

@forecasts_bp.route('', methods=['GET'])
@token_required
def get_forecast(current_user_id):
    """
    Project future financial standing based on historical data and current budget
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: Financial projection
    """
    today = datetime.utcnow().date()
    
    # 1. Calculate Current Balance
    total_income = db.session.query(func.sum(Income.amount)).filter_by(user_id=current_user_id).scalar() or 0
    total_expense = db.session.query(func.sum(Expense.amount)).filter_by(user_id=current_user_id).scalar() or 0
    current_balance = total_income - total_expense

    # 2. Daily Burn Rate (last 60 days)
    sixty_days_ago = today - timedelta(days=60)
    expenses_60 = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user_id,
        Expense.date >= sixty_days_ago
    ).scalar() or 0
    daily_burn = expenses_60 / 60.0

    # 3. Daily Income
    # Try manual income for this month first
    month_str = today.strftime('%Y-%m')
    manual_income = MonthlyIncome.query.filter_by(user_id=current_user_id, month=month_str).first()
    if manual_income:
        daily_income = manual_income.amount / 30.0
    else:
        incomes_60 = db.session.query(func.sum(Income.amount)).filter(
            Income.user_id == current_user_id,
            Income.date >= sixty_days_ago
        ).scalar() or 0
        daily_income = incomes_60 / 60.0

    # 4. Correct for Budget (current month remaining)
    # This adds realism: if the user hasn't spent their budget yet, it's a "planned expense"
    budgets = Budget.query.filter_by(user_id=current_user_id, month=month_str).all()
    total_budget = sum(b.amount for b in budgets)
    month_start = today.replace(day=1)
    spent_this_month = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user_id,
        Expense.date >= month_start
    ).scalar() or 0
    remaining_budget = max(0, total_budget - spent_this_month)

    # 5. Projection logic (90 days)
    projection = []
    temp_balance = current_balance
    
    # Account for remaining budget as an upfront hit or spread? 
    # Let's spread the remaining budget over the rest of the month for the chart
    days_in_month = (month_start + timedelta(days=32)).replace(day=1) - month_start
    days_left = (month_start + days_in_month - today).days
    extra_daily_expense = remaining_budget / max(days_left, 1)

    for i in range(91):
        target_date = today + timedelta(days=i)
        
        # Simple linear projection
        # In early days of the month, we add the 'planned' extra expense
        current_daily_burn = daily_burn
        if i < days_left:
            current_daily_burn += extra_daily_expense
            
        projection.append({
            'date': target_date.isoformat(),
            'balance': round(temp_balance, 2)
        })
        
        temp_balance += (daily_income - current_daily_burn)

    return jsonify({
        'current_balance': round(current_balance, 2),
        'daily_burn': round(daily_burn, 2),
        'daily_income': round(daily_income, 2),
        'projection': projection
    }), 200
