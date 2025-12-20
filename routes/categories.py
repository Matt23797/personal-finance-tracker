from flask import Blueprint, request, jsonify
from models import db, Category, CategoryMapping, EXPENSE_CATEGORIES, Expense, Budget
from routes.auth import token_required

categories_bp = Blueprint('categories', __name__, url_prefix='/api/categories')

@categories_bp.route('', methods=['GET'])
@token_required
def get_categories(current_user_id):
    """
    Get list of user-defined categories. Seeds default if none exist.
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: List of category names
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

@categories_bp.route('/extended', methods=['GET'])
@token_required
def get_categories_extended(current_user_id):
    """
    Get full category objects (id and name)
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: List of category objects
    """
    categories = Category.query.filter_by(user_id=current_user_id).all()
    return jsonify([c.to_dict() for c in categories]), 200

@categories_bp.route('', methods=['POST'])
@token_required
def add_category(current_user_id):
    """
    Add a new custom category
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
            name:
              type: string
    responses:
      201:
        description: Category added
    """
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

@categories_bp.route('/<int:cat_id>', methods=['PUT'])
@token_required
def update_category_name(current_user_id, cat_id):
    """
    Rename a category and cascade to existing expenses/budgets
    ---
    security:
      - Bearer: []
    parameters:
      - name: cat_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
    responses:
      200:
        description: Category renamed
    """
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

@categories_bp.route('/<int:cat_id>', methods=['DELETE'])
@token_required
def delete_category(current_user_id, cat_id):
    """
    Delete a category and set affected expenses/budgets to 'Other'
    ---
    security:
      - Bearer: []
    parameters:
      - name: cat_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Category deleted
    """
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

@categories_bp.route('/suggest', methods=['POST'])
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
