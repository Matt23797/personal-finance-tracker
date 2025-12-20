from flask import Blueprint, request, jsonify
from models import db, Budget, Income, Expense, MonthlyIncome
from datetime import datetime, timedelta
from routes.auth import token_required
from sqlalchemy import func

budget_bp = Blueprint('budget', __name__, url_prefix='/api/budget')

@budget_bp.route('', methods=['POST'])
@token_required
def set_budget(current_user_id):
    """
    Set or update a budget limit for a category
    ---
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            category:
              type: string
            amount:
              type: number
            month:
              type: string
              description: Format YYYY-MM
    responses:
      200:
        description: Budget saved
    """
    data = request.get_json()
    category = data.get('category')
    amount = data.get('amount')
    month = data.get('month', datetime.now().strftime('%Y-%m'))
    
    if not category or amount is None:
        return jsonify({'message': 'Category and amount are required'}), 400
        
    existing = Budget.query.filter_by(user_id=current_user_id, category=category, month=month).first()
    if existing:
        existing.amount = amount
    else:
        new_budget = Budget(user_id=current_user_id, category=category, amount=amount, month=month)
        db.session.add(new_budget)
        
    db.session.commit()
    return jsonify({'message': 'Budget saved'}), 200

@budget_bp.route('/income', methods=['POST'])
@token_required
def set_monthly_income(current_user_id):
    """
    Set manual income for a month
    ---
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            amount:
              type: number
            month:
              type: string
              description: Format YYYY-MM
    responses:
      200:
        description: Income saved
    """
    data = request.get_json()
    amount = data.get('amount')
    month = data.get('month', datetime.now().strftime('%Y-%m'))
    
    if amount is None:
        return jsonify({'message': 'Amount is required'}), 400
        
    existing = MonthlyIncome.query.filter_by(user_id=current_user_id, month=month).first()
    if existing:
        existing.amount = amount
    else:
        new_income = MonthlyIncome(user_id=current_user_id, month=month, amount=amount)
        db.session.add(new_income)
        
    db.session.commit()
    return jsonify({'message': 'Income saved'}), 200

@budget_bp.route('/projection', methods=['GET'])
@token_required
def get_projection(current_user_id):
    """
    Calculate projected income based on history or manual override
    ---
    security:
      - Bearer: []
    parameters:
      - name: month
        in: query
        type: string
        description: Format YYYY-MM
    responses:
      200:
        description: Projected income details
    """
    today = datetime.now()
    month_str = request.args.get('month', today.strftime('%Y-%m'))
    
    # Check for manual entry first
    manual_income = MonthlyIncome.query.filter_by(user_id=current_user_id, month=month_str).first()
    if manual_income:
        return jsonify({
            'projected_income': manual_income.amount,
            'is_manual': True,
            'months_analyzed': 0
        }), 200

    three_months_ago = today - timedelta(days=90)
    
    # Get total income for last 3 months
    total_income = db.session.query(func.sum(Income.amount)).filter(
        Income.user_id == current_user_id,
        Income.date >= three_months_ago
    ).scalar() or 0.0
    
    # Count distinct months
    incomes = db.session.query(Income.date).filter(
        Income.user_id == current_user_id,
        Income.date >= three_months_ago
    ).all()
    
    distinct_months = set()
    for (d,) in incomes:
        distinct_months.add(d.strftime('%Y-%m'))
        
    num_months = len(distinct_months)
    divisor = max(num_months, 1)
    
    monthly_average = total_income / float(divisor)
    
    return jsonify({
        'projected_income': round(monthly_average, 2),
        'is_manual': False,
        'months_analyzed': divisor
    }), 200

@budget_bp.route('/status', methods=['GET'])
@token_required
def get_status(current_user_id):
    """
    Get status of current month's budget vs actuals
    ---
    security:
      - Bearer: []
    parameters:
      - name: month
        in: query
        type: string
        description: Format YYYY-MM
    responses:
      200:
        description: Budget and spending breakdown
    """
    month_str = request.args.get('month', datetime.now().strftime('%Y-%m'))
    start_date = datetime.strptime(month_str, '%Y-%m')
    # Simple logic to get end of month
    if start_date.month == 12:
        end_date = datetime(start_date.year + 1, 1, 1)
    else:
        end_date = datetime(start_date.year, start_date.month + 1, 1)
        
    # Get all budgets
    budgets = Budget.query.filter_by(user_id=current_user_id, month=month_str).all()
    budget_map = {b.category: b.amount for b in budgets}
    
    # Get all expenses for this month
    expenses = db.session.query(
        Expense.category, 
        func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user_id,
        Expense.date >= start_date,
        Expense.date < end_date
    ).group_by(Expense.category).all()
    
    actual_map = {cat: amt for cat, amt in expenses}
    
    # Combine
    all_categories = set(budget_map.keys()) | set(actual_map.keys())
    result = []
    
    total_budget = 0
    total_spent = 0
    
    for cat in all_categories:
        budget = budget_map.get(cat, 0)
        spent = actual_map.get(cat, 0)
        
        total_budget += budget
        total_spent += spent
        
        result.append({
            'category': cat,
            'budget': budget,
            'spent': spent,
            'remaining': budget - spent,
            'percent': (spent / budget * 100) if budget > 0 else (100 if spent > 0 else 0)
        })
        
    return jsonify({
        'categories': result,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'month': month_str
    }), 200

@budget_bp.route('/<category>', methods=['DELETE'])
@token_required
def delete_budget(current_user_id, category):
    """
    Remove the budget for a specific category
    ---
    security:
      - Bearer: []
    parameters:
      - name: category
        in: path
        type: string
        required: true
      - name: month
        in: query
        type: string
        description: Format YYYY-MM
    responses:
      200:
        description: Budget deleted
    """
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    budget = Budget.query.filter_by(user_id=current_user_id, category=category, month=month).first()
    if budget:
        db.session.delete(budget)
        db.session.commit()
    return jsonify({'message': 'Budget deleted'}), 200
