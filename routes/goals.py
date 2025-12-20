from flask import Blueprint, request, jsonify
from models import db, Goal
from routes.auth import token_required
from datetime import datetime

goals_bp = Blueprint('goals', __name__, url_prefix='/api/goals')

@goals_bp.route('', methods=['POST'])
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

@goals_bp.route('', methods=['GET'])
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

@goals_bp.route('/<int:goal_id>', methods=['PUT'])
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

@goals_bp.route('/<int:goal_id>', methods=['DELETE'])
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
