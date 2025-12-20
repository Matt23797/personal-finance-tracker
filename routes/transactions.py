from flask import Blueprint, request, jsonify
from models import db, Income, Expense, CategoryMapping
from routes.auth import token_required
from datetime import datetime
from sqlalchemy import func

transactions_bp = Blueprint('transactions', __name__, url_prefix='/api')

@transactions_bp.route('/incomes', methods=['POST'])
@token_required
def add_income(current_user_id):
    """
    Add a new income
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
            source:
              type: string
            date:
              type: string
              format: date
    responses:
      201:
        description: Income added
    """
    data = request.get_json()
    new_income = Income(
        user_id=current_user_id,
        amount=data['amount'],
        source=data['source'],
        date=datetime.strptime(data['date'], '%Y-%m-%d').date() if 'date' in data else datetime.utcnow().date()
    )
    db.session.add(new_income)
    db.session.commit()
    return jsonify({'message': 'Income added'}), 201

@transactions_bp.route('/incomes', methods=['GET'])
@token_required
def get_incomes(current_user_id):
    """
    Get all incomes for user
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: List of incomes
    """
    incomes = Income.query.filter_by(user_id=current_user_id).all()
    return jsonify([i.to_dict() for i in incomes]), 200

@transactions_bp.route('/expenses', methods=['POST'])
@token_required
def add_expense(current_user_id):
    """
    Add a new expense
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
            category:
              type: string
            description:
              type: string
            date:
              type: string
              format: date
    responses:
      201:
        description: Expense added
    """
    data = request.get_json()
    description = data.get('description', '')
    category = data['category']
    
    new_expense = Expense(
        user_id=current_user_id,
        amount=data['amount'],
        category=category,
        description=description,
        date=datetime.strptime(data['date'], '%Y-%m-%d').date() if 'date' in data else datetime.utcnow().date()
    )
    db.session.add(new_expense)
    
    # Learn categorization if description is provided
    if description:
        keyword = description.lower().strip()
        existing_mapping = CategoryMapping.query.filter_by(
            user_id=current_user_id, 
            keyword=keyword
        ).first()
        
        if existing_mapping:
            if existing_mapping.category == category:
                existing_mapping.count += 1
            else:
                existing_mapping.category = category
                existing_mapping.count = 1
        else:
            new_mapping = CategoryMapping(
                user_id=current_user_id,
                keyword=keyword,
                category=category
            )
            db.session.add(new_mapping)
    
    db.session.commit()
    return jsonify({'message': 'Expense added'}), 201

@transactions_bp.route('/expenses', methods=['GET'])
@token_required
def get_expenses(current_user_id):
    """
    Get all expenses for user
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: List of expenses
    """
    expenses = Expense.query.filter_by(user_id=current_user_id).all()
    return jsonify([e.to_dict() for e in expenses]), 200

@transactions_bp.route('/summary', methods=['GET'])
@token_required
def get_summary(current_user_id):
    """
    Get financial summary (supports date filtering)
    ---
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
    responses:
      200:
        description: Summary of finances
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    income_query = Income.query.filter_by(user_id=current_user_id)
    expense_query = Expense.query.filter_by(user_id=current_user_id)

    if start_date:
        try:
            dt_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            income_query = income_query.filter(Income.date >= dt_start)
            expense_query = expense_query.filter(Expense.date >= dt_start)
        except ValueError:
            pass
            
    if end_date:
        try:
            dt_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            income_query = income_query.filter(Income.date <= dt_end)
            expense_query = expense_query.filter(Expense.date <= dt_end)
        except ValueError:
            pass

    incomes = income_query.all()
    expenses = expense_query.all()
    
    total_income = sum(i.amount for i in incomes)
    total_expense = sum(e.amount for e in expenses)
    
    return jsonify({
        'total_income': total_income,
        'total_expense': total_expense
    }), 200

@transactions_bp.route('/expenses/<int:expense_id>', methods=['PUT'])
@token_required
def update_expense(current_user_id, expense_id):
    """
    Update an expense (category, amount, etc.)
    ---
    security:
      - Bearer: []
    parameters:
      - name: expense_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            category:
              type: string
            amount:
              type: number
            description:
              type: string
            date:
              type: string
    responses:
      200:
        description: Expense updated
    """
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user_id).first()
    if not expense:
        return jsonify({'message': 'Expense not found'}), 404
        
    data = request.get_json()
    
    if 'category' in data:
        expense.category = data['category']
        if expense.description:
            keyword = expense.description.lower().strip()
            mapping = CategoryMapping.query.filter_by(user_id=current_user_id, keyword=keyword).first()
            if mapping:
                mapping.category = data['category']
                mapping.count += 1
            else:
                new_mapping = CategoryMapping(user_id=current_user_id, keyword=keyword, category=data['category'])
                db.session.add(new_mapping)
                
    if 'amount' in data:
        expense.amount = data['amount']
    if 'description' in data:
        expense.description = data['description']
    if 'date' in data:
        expense.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        
    db.session.commit()
    return jsonify({'message': 'Expense updated'}), 200

@transactions_bp.route('/expenses/by-category', methods=['GET'])
@token_required
def get_expenses_by_category(current_user_id):
    """
    Get expense breakdown by category (supports date filtering)
    ---
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
    responses:
      200:
        description: Category breakdown with amounts
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Expense.query.filter_by(user_id=current_user_id)

    if start_date:
        try:
            dt_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= dt_start)
        except ValueError:
            pass
            
    if end_date:
        try:
            dt_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= dt_end)
        except ValueError:
            pass

    expenses = query.all()
    breakdown = {}
    for expense in expenses:
        if expense.category in breakdown:
            breakdown[expense.category] += expense.amount
        else:
            breakdown[expense.category] = expense.amount
    
    return jsonify(breakdown), 200

@transactions_bp.route('/expenses/bulk-update', methods=['POST'])
@token_required
def bulk_update_expenses(current_user_id):
    """
    Bulk update expense categories
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
            ids:
              type: array
              items:
                type: integer
            category:
              type: string
    responses:
      200:
        description: Expenses updated successfully
    """
    data = request.get_json()
    expense_ids = data.get('ids', [])
    new_category = data.get('category')

    if not expense_ids or not new_category:
        return jsonify({'message': 'Missing IDs or category'}), 400

    Expense.query.filter(Expense.user_id == current_user_id, Expense.id.in_(expense_ids)).update(
        {Expense.category: new_category}, synchronize_session=False
    )
    db.session.commit()

    return jsonify({'message': f'Updated {len(expense_ids)} expenses successfully'}), 200
