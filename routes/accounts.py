from flask import Blueprint, request, jsonify
from models import db, Account
from routes.auth import token_required
from datetime import datetime

accounts_bp = Blueprint('accounts', __name__, url_prefix='/api/accounts')

@accounts_bp.route('', methods=['GET'])
@token_required
def get_accounts(current_user_id):
    accounts = Account.query.filter_by(user_id=current_user_id).all()
    
    return jsonify([{
        'id': a.id,
        'name': a.name,
        'balance': float(a.balance),
        'type': a.type,
        'is_manual': a.is_manual,
        'last_synced': a.last_synced.isoformat() if a.last_synced else None
    } for a in accounts]), 200

@accounts_bp.route('', methods=['POST'])
@token_required
def create_account(current_user_id):
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'message': 'Name is required'}), 400
        
    try:
        balance = float(data.get('balance', 0.0))
    except ValueError:
        return jsonify({'message': 'Invalid balance'}), 400

    new_account = Account(
        user_id=current_user_id,
        name=data['name'],
        balance=balance,
        type=data.get('type', 'checking'),
        is_manual=True,
        last_synced=datetime.utcnow()
    )
    
    db.session.add(new_account)
    db.session.commit()
    
    return jsonify({'message': 'Account created', 'id': new_account.id}), 201

@accounts_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_account(current_user_id, id):
    account = Account.query.filter_by(id=id, user_id=current_user_id).first()
    if not account:
        return jsonify({'message': 'Account not found'}), 404
        
    data = request.get_json()
    
    if 'balance' in data:
        try:
            account.balance = float(data['balance'])
            # Updating balance manually should count as a sync
            account.last_synced = datetime.utcnow()
        except ValueError:
            return jsonify({'message': 'Invalid balance'}), 400
            
    if 'name' in data:
        account.name = data['name']
        
    if 'type' in data:
        account.type = data['type']

    db.session.commit()
    return jsonify({'message': 'Account updated'}), 200

@accounts_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_account(current_user_id, id):
    account = Account.query.filter_by(id=id, user_id=current_user_id).first()
    if not account:
        return jsonify({'message': 'Account not found'}), 404
        
    # Cascade delete is configured in DB, but SQLAlchemy might need help if not db.ForeignKey with ON DELETE CASCADE
    # We defined ondelete='CASCADE' in models, so simple delete should work.
    
    db.session.delete(account)
    db.session.commit()
    return jsonify({'message': 'Account deleted'}), 200
