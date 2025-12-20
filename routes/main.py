from flask import Blueprint, request, jsonify
from models import db, Income, Expense, Goal, CategoryMapping, EXPENSE_CATEGORIES, User, Budget, MonthlyIncome, Category
from functools import wraps
import jwt
import os
from datetime import datetime
from sqlalchemy import func
import hashlib
import csv
import io
from ofxparse import OfxParser
from routes.auth import token_required
from utils import auto_categorize

main_bp = Blueprint('main', __name__, url_prefix='/api')

# Web routes should be separate from API routes ideally, or attached to app directly.
# But since this is a simple app, we likely have web routes defined in app.py calling render_template?
# Let's check app.py again to see where other page routes are.
# Wait, based on Step 22 (view app.py), page routes interact with templates directly. 
# "routes/main.py" has url_prefix='/api', so putting it here would make it /api/budget (HTML).
# We want /budget.
# So I should edit app.py instead for the page route.



@main_bp.route('/incomes', methods=['POST'])
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

@main_bp.route('/incomes', methods=['GET'])
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

@main_bp.route('/expenses', methods=['POST'])
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
        # Extract keywords (simple approach: use the description as keyword)
        keyword = description.lower().strip()
        existing_mapping = CategoryMapping.query.filter_by(
            user_id=current_user_id, 
            keyword=keyword
        ).first()
        
        if existing_mapping:
            if existing_mapping.category == category:
                existing_mapping.count += 1
            else:
                # User recategorized, update to new category
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

@main_bp.route('/expenses', methods=['GET'])
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

@main_bp.route('/summary', methods=['GET'])
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

@main_bp.route('/expenses/<int:expense_id>', methods=['PUT'])
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
        # Update learning (mapping) if description exists
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

# ============== GOALS ==============

@main_bp.route('/goals', methods=['POST'])
@token_required
def add_goal(current_user_id):
    """
    Add a new financial goal
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
            description:
              type: string
            target_amount:
              type: number
            deadline:
              type: string
              format: date
    responses:
      201:
        description: Goal added
    """
    data = request.get_json()
    new_goal = Goal(
        user_id=current_user_id,
        description=data['description'],
        target_amount=data['target_amount'],
        current_amount=data.get('current_amount', 0),
        deadline=datetime.strptime(data['deadline'], '%Y-%m-%d').date() if 'deadline' in data else None
    )
    db.session.add(new_goal)
    db.session.commit()
    return jsonify({'message': 'Goal added', 'id': new_goal.id}), 201

@main_bp.route('/goals', methods=['GET'])
@token_required
def get_goals(current_user_id):
    """
    Get all goals for user
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: List of goals
    """
    goals = Goal.query.filter_by(user_id=current_user_id).all()
    return jsonify([g.to_dict() for g in goals]), 200

@main_bp.route('/goals/<int:goal_id>', methods=['PUT'])
@token_required
def update_goal(current_user_id, goal_id):
    """
    Update a goal (e.g., current_amount)
    ---
    security:
      - Bearer: []
    parameters:
      - name: goal_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            current_amount:
              type: number
            description:
              type: string
            target_amount:
              type: number
            deadline:
              type: string
    responses:
      200:
        description: Goal updated
    """
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user_id).first()
    if not goal:
        return jsonify({'message': 'Goal not found'}), 404
    
    data = request.get_json()
    if 'current_amount' in data:
        goal.current_amount = data['current_amount']
    if 'description' in data:
        goal.description = data['description']
    if 'target_amount' in data:
        goal.target_amount = data['target_amount']
    if 'deadline' in data:
        goal.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date() if data['deadline'] else None
    
    db.session.commit()
    return jsonify({'message': 'Goal updated'}), 200

@main_bp.route('/goals/<int:goal_id>', methods=['DELETE'])
@token_required
def delete_goal(current_user_id, goal_id):
    """
    Delete a goal
    ---
    security:
      - Bearer: []
    parameters:
      - name: goal_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Goal deleted
    """
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user_id).first()
    if not goal:
        return jsonify({'message': 'Goal not found'}), 404
    
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"message": "Goal deleted"}), 200


def process_ofx(content, user_id):
    imported = 0
    duplicates = 0
    try:
        ofx = OfxParser.parse(io.BytesIO(content))
        for account in ofx.accounts:
            for tx in account.statement.transactions:
                # Use OFX unique ID
                unique_id = f"ofx_{tx.id}"
                
                exists = Expense.query.filter_by(simplefin_id=unique_id).first() or \
                         Income.query.filter_by(simplefin_id=unique_id).first()
                if exists:
                    duplicates += 1
                    continue
                
                desc = tx.payee or tx.memo or 'Unknown OFX Transaction'
                category = auto_categorize(desc, user_id)
                
                if tx.amount < 0:
                    new_item = Expense(user_id=user_id, amount=abs(tx.amount), category=category, description=desc, date=tx.date.date(), simplefin_id=unique_id)
                else:
                    new_item = Income(user_id=user_id, amount=tx.amount, source=desc, date=tx.date.date(), simplefin_id=unique_id)
                db.session.add(new_item)
                imported += 1
    except Exception as e:
        print(f"Error parsing OFX: {e}")
    return imported, duplicates

def process_csv(content, user_id):
    stream = io.StringIO(content.decode('utf-8'))
    reader = csv.DictReader(stream)
    
    headers = reader.fieldnames
    if not headers: return 0, 0

    date_col = next((h for h in headers if 'date' in h.lower()), None)
    desc_col = next((h for h in headers if any(k in h.lower() for k in ['desc', 'payee', 'memo', 'name'])), None)
    amount_col = next((h for h in headers if any(k in h.lower() for k in ['amount', 'value', 'total', 'price'])), None)

    if not date_col or not desc_col or not amount_col:
        return 0, 0

    imported = 0
    duplicates = 0

    for row in reader:
        try:
            date_str = row[date_col]
            desc = row[desc_col]
            amount_raw = row[amount_col].replace('$', '').replace(',', '')
            amount = float(amount_raw)
            
            dt = None
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y"):
                try:
                    dt = datetime.strptime(date_str, fmt).date()
                    break
                except: continue
            
            if not dt: continue

            # Content-based hash for CSV deduplication
            raw_id = f"csv_{dt}_{desc}_{amount}_{user_id}"
            unique_id = hashlib.sha256(raw_id.encode()).hexdigest()[:32]

            exists = Expense.query.filter_by(simplefin_id=unique_id).first() or \
                     Income.query.filter_by(simplefin_id=unique_id).first()
            if exists:
                duplicates += 1
                continue

            category = auto_categorize(desc, user_id)
            if amount < 0:
                new_item = Expense(user_id=user_id, amount=abs(amount), category=category, description=desc, date=dt, simplefin_id=unique_id)
            else:
                new_item = Income(user_id=user_id, amount=amount, source=desc, date=dt, simplefin_id=unique_id)
            
            db.session.add(new_item)
            imported += 1
        except: continue
    
    return imported, duplicates

@main_bp.route('/transactions/import', methods=['POST'])
@token_required
def import_transactions(current_user_id):
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename = file.filename.lower()
    content = file.read()
    
    if filename.endswith(('.ofx', '.qfx')):
        imported, duplicates = process_ofx(content, current_user_id)
    elif filename.endswith('.csv'):
        imported, duplicates = process_csv(content, current_user_id)
    else:
        return jsonify({"error": "Unsupported file format. Please use CSV, OFX, or QFX."}), 400

    db.session.commit()
    return jsonify({
        "message": f"Successfully imported {imported} transactions.",
        "duplicates": duplicates
    }), 200

# ============== EXPENSE CATEGORIES ==============

@main_bp.route('/categories', methods=['GET'])
@token_required
def get_categories(current_user_id):
    """
    Get list of user-defined categories. Seeds default if none exist.
    """
    categories = Category.query.filter_by(user_id=current_user_id).all()
    
    if not categories:
        # Seed default categories
        for cat_name in EXPENSE_CATEGORIES:
            new_cat = Category(user_id=current_user_id, name=cat_name)
            db.session.add(new_cat)
        db.session.commit()
        categories = Category.query.filter_by(user_id=current_user_id).all()
        
    return jsonify([c.name for c in categories]), 200

@main_bp.route('/categories/extended', methods=['GET'])
@token_required
def get_categories_extended(current_user_id):
    """
    Get full category objects (id and name)
    """
    categories = Category.query.filter_by(user_id=current_user_id).all()
    return jsonify([c.to_dict() for c in categories]), 200

@main_bp.route('/categories', methods=['POST'])
@token_required
def add_category(current_user_id):
    """Add a new custom category"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'message': 'Category name is required'}), 400
        
    existing = Category.query.filter_by(user_id=current_user_id, name=name).first()
    if existing:
        return jsonify({'message': 'Category already exists'}), 400
        
    new_cat = Category(user_id=current_user_id, name=name)
    db.session.add(new_cat)
    db.session.commit()
    return jsonify(new_cat.to_dict()), 201

@main_bp.route('/categories/<int:cat_id>', methods=['PUT'])
@token_required
def update_category_name(current_user_id, cat_id):
    """Rename a category and cascade to existing expenses/budgets"""
    category = Category.query.filter_by(id=cat_id, user_id=current_user_id).first()
    if not category:
        return jsonify({'message': 'Category not found'}), 404
        
    data = request.get_json()
    new_name = data.get('name', '').strip()
    
    if not new_name:
        return jsonify({'message': 'New name is required'}), 400
        
    old_name = category.name
    category.name = new_name
    
    # Cascade updates
    Expense.query.filter_by(user_id=current_user_id, category=old_name).update({Expense.category: new_name})
    Budget.query.filter_by(user_id=current_user_id, category=old_name).update({Budget.category: new_name})
    CategoryMapping.query.filter_by(user_id=current_user_id, category=old_name).update({CategoryMapping.category: new_name})
    
    db.session.commit()
    return jsonify({'message': 'Category renamed successfully'}), 200

@main_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
@token_required
def delete_category(current_user_id, cat_id):
    """Delete a category and set affected expenses/budgets to 'Other'"""
    category = Category.query.filter_by(id=cat_id, user_id=current_user_id).first()
    if not category:
        return jsonify({'message': 'Category not found'}), 404
        
    old_name = category.name
    
    # Ensure 'Other' exists for the user
    other = Category.query.filter_by(user_id=current_user_id, name='Other').first()
    if not other and old_name != 'Other':
        other = Category(user_id=current_user_id, name='Other')
        db.session.add(other)
        db.session.commit()
    
    if old_name != 'Other':
        Expense.query.filter_by(user_id=current_user_id, category=old_name).update({Expense.category: 'Other'})
        Budget.query.filter_by(user_id=current_user_id, category=old_name).update({Budget.category: 'Other'})
        CategoryMapping.query.filter_by(user_id=current_user_id, category=old_name).update({CategoryMapping.category: 'Other'})
        db.session.delete(category)
        db.session.commit()
        return jsonify({'message': 'Category deleted successfully'}), 200
    else:
        return jsonify({'message': 'Cannot delete the "Other" category'}), 400

@main_bp.route('/expenses/by-category', methods=['GET'])
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

@main_bp.route('/suggest-category', methods=['POST'])
@token_required
def suggest_category(current_user_id):
    """
    Suggest a category based on description (uses learned patterns)
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
            description:
              type: string
    responses:
      200:
        description: Suggested category
    """
    data = request.get_json()
    description = data.get('description', '').lower().strip()
    
    if not description:
        return jsonify({'suggested_category': None}), 200
    
    # Look for exact match first
    mapping = CategoryMapping.query.filter_by(
        user_id=current_user_id,
        keyword=description
    ).first()
    
    if mapping:
        return jsonify({'suggested_category': mapping.category, 'confidence': 'high'}), 200
    
    # Look for partial match
    mappings = CategoryMapping.query.filter_by(user_id=current_user_id).all()
    for m in mappings:
        if m.keyword in description or description in m.keyword:
            return jsonify({'suggested_category': m.category, 'confidence': 'medium'}), 200
    
    return jsonify({'suggested_category': None, 'confidence': None}), 200

@main_bp.route('/expenses/bulk-update', methods=['POST'])
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

# ============== SIMPLEFIN STATUS ==============

@main_bp.route('/forecast', methods=['GET'])
@token_required
def get_forecast(current_user_id):
    """
    Project future financial standing based on historical data and current budget
    """
    from models import MonthlyIncome, Budget, db
    from sqlalchemy import func
    from datetime import timedelta

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

@main_bp.route('/simplefin/status', methods=['GET'])
@token_required
def simplefin_status(current_user_id):
    """
    Check if SimpleFin is connected
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: Connection status
    """
    import os
    user = User.query.get(current_user_id)
    # Check DB token OR env var
    connected = (user.simplefin_token is not None and user.simplefin_token != '') or \
                (os.environ.get('SIMPLEFIN_TOKEN') is not None)
    return jsonify({'connected': connected}), 200

# ============== BUDGET ==============

@main_bp.route('/budget', methods=['POST'])
@token_required
def set_budget(current_user_id):
    """Set or update a budget limit for a category"""
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

@main_bp.route('/budget/<category>', methods=['DELETE'])
@token_required
def delete_budget(current_user_id, category):
    """Delete a budget for a category and month"""
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    budget = Budget.query.filter_by(user_id=current_user_id, category=category, month=month).first()
    if not budget:
        return jsonify({'message': 'Budget not found'}), 404
    
    db.session.delete(budget)
    db.session.commit()
    return jsonify({'message': 'Budget deleted'}), 200

@main_bp.route('/budget/income', methods=['POST'])
@token_required
def set_monthly_income(current_user_id):
    """Set manual income for a month"""
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

@main_bp.route('/budget/projection', methods=['GET'])
@token_required
def get_projection(current_user_id):
    """Calculate projected income based on available history (up to 3 months) OR manual override"""
    from datetime import timedelta
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

@main_bp.route('/budget/status', methods=['GET'])
@token_required
def get_status(current_user_id):
    """Get status of current month's budget vs actuals"""
    month_str = request.args.get('month', datetime.now().strftime('%Y-%m'))
    try:
        start_date = datetime.strptime(month_str, '%Y-%m')
    except ValueError:
        return jsonify({'message': 'Invalid month format'}), 400

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
        Expense.date >= start_date.date(),
        Expense.date < end_date.date()
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
