from flask import Blueprint, request, jsonify, current_app
from models import db, User
from functools import wraps
from cryptography.fernet import Fernet
import jwt
import os
import requests
import base64

simplefin_bp = Blueprint('simplefin', __name__, url_prefix='/simplefin')

# Get or generate encryption key (store this securely!)
def get_encryption_key():
    key = os.environ.get('ENCRYPTION_KEY')
    key_file = 'finance.key'
    
    if not key:
        # Check for local key file
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read().decode().strip()
        
        if not key:
            # Generate and save to file
            key = Fernet.generate_key().decode()
            with open(key_file, 'w') as f:
                f.write(key)
            # Set restrictive permissions (read/write for owner only) on Unix-like systems
            # On Windows, basic file creation is default, but we can't easily set chmod 600 in a cross-platform standard library way without extra modules
            # Relying on .gitignore for repo security
            
            os.environ['ENCRYPTION_KEY'] = key
            
    return key.encode() if isinstance(key, str) else key

def encrypt_token(token):
    """Encrypt a token using Fernet symmetric encryption"""
    f = Fernet(get_encryption_key())
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token):
    """Decrypt an encrypted token"""
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted_token.encode()).decode()

from routes.auth import token_required

def claim_setup_token(setup_token):
    """
    Claim a SimpleFin setup token to get the access URL.
    Setup token format: base64 encoded URL like https://beta-bridge.simplefin.org/simplefin/create/XXXXXX
    Returns the access URL in format: https://user:pass@beta-bridge.simplefin.org/simplefin
    """
    try:
        # If it looks like a URL already, try to decode it as base64 first
        if not setup_token.startswith('http'):
            # It's base64 encoded, decode it
            claim_url = base64.b64decode(setup_token).decode('utf-8')
        else:
            # It's already a URL (user pasted the decoded version)
            claim_url = setup_token
        
        current_app.logger.info(f"[SimpleFin] Claiming token at: {claim_url}")
        
        # POST to the claim URL to get the access URL
        response = requests.post(claim_url, timeout=30)
        
        current_app.logger.info(f"[SimpleFin] Claim response status: {response.status_code}")
        current_app.logger.info(f"[SimpleFin] Claim response: {response.text[:200] if response.text else 'empty'}")
        
        if response.status_code == 200:
            access_url = response.text.strip()
            return {'success': True, 'access_url': access_url}
        else:
            return {'success': False, 'error': f"Claim failed with status {response.status_code}: {response.text}"}
            
    except Exception as e:
        current_app.logger.error(f"[SimpleFin] Error claiming token: {str(e)}")
        return {'success': False, 'error': str(e)}

@simplefin_bp.route('/save-key', methods=['POST'])
@token_required
def save_key(current_user_id):
    """
    Save SimpleFin setup token or access URL (encrypted)
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
            access_key:
              type: string
              description: SimpleFin setup token (base64) or access URL
    responses:
      200:
        description: Key saved successfully
    """
    data = request.get_json()
    access_key = data.get('access_key', '').strip()
    
    if not access_key:
        return jsonify({'message': 'Access key is required'}), 400
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Check if this is a setup token that needs to be claimed
    # Setup tokens are either base64 or URLs containing /create/
    is_setup_token = '/create/' in access_key or (not access_key.startswith('https://') and len(access_key) > 50)
    
    if is_setup_token or (access_key.startswith('http') and '/create/' in access_key):
        result = claim_setup_token(access_key)
        if result['success']:
            access_key = result['access_url']
            current_app.logger.info(f"[SimpleFin] Successfully claimed, got access URL")
        else:
            return jsonify({'message': 'Failed to claim setup token', 'error': result['error']}), 400
    
    # Encrypt and store the access key/URL
    encrypted_key = encrypt_token(access_key)
    user.simplefin_token = encrypted_key
    db.session.commit()
    
    return jsonify({'message': 'SimpleFin key saved successfully'}), 200

@simplefin_bp.route('/disconnect', methods=['POST'])
@token_required
def disconnect(current_user_id):
    """
    Disconnect SimpleFin (remove stored key)
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: Disconnected successfully
    """
    user = User.query.get(current_user_id)
    if user:
        user.simplefin_token = None
        db.session.commit()
    
    return jsonify({'message': 'SimpleFin disconnected'}), 200

@simplefin_bp.route('/sync', methods=['POST'])
@token_required  
def sync_accounts(current_user_id):
    """
    Sync accounts and transactions from SimpleFin
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: Synced data from SimpleFin
    """
    user = User.query.get(current_user_id)
    
    # Try DB token first, then Env var
    access_url = None
    if user and user.simplefin_token:
        access_url = decrypt_token(user.simplefin_token)
    elif os.environ.get('SIMPLEFIN_TOKEN'):
        access_url = os.environ.get('SIMPLEFIN_TOKEN')
        
    if not access_url:
        return jsonify({'message': 'SimpleFin not connected'}), 401
    
    from models import Income, Expense, CategoryMapping
    from datetime import datetime, timedelta
    
    try:
        current_app.logger.info(f"[SimpleFin] Syncing with access URL: {access_url[:20]}...")
        
        # Calculate date range (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # SimpleFin access URL format: https://.../simplefin
        # Append date range to get transactions embedded in accounts
        # SimpleFin expects start-date and end-date params (sometimes start_date/end_date)
        # Using standard 'start-date' based on common SimpleFin usage
        accounts_url = f"{access_url}/accounts?start-date={int(start_date.timestamp())}&end-date={int(end_date.timestamp())}"
        
        response = requests.get(accounts_url, timeout=30)
        
        current_app.logger.info(f"[SimpleFin] Sync response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            accounts = data.get('accounts', [])
            synced_count = 0
            
            for account in accounts:
                transactions = account.get('transactions', [])
                for txn in transactions:
                    # SimpleFin transaction structure (typical):
                    # {'id': '...', 'posted': timestamp, 'amount': '12.34', 'description': '...', 'payee': '...', 'category': '...'}
                    
                    txn_id = txn.get('id')
                    if not txn_id: 
                        continue
                        
                    # Check if already exists in either table
                    existing_income = Income.query.filter_by(simplefin_id=txn_id).first()
                    existing_expense = Expense.query.filter_by(simplefin_id=txn_id).first()
                    
                    if existing_income or existing_expense:
                        continue
                        
                    # Process Amount (SimpleFin: usually negative for debit/expense, positive for credit/income)
                    # Some versions might invert it, but standard is - = money leaving
                    try:
                        amount = float(txn.get('amount', 0))
                    except:
                        continue
                        
                    timestamp = txn.get('posted')
                    txn_date = datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow()
                    description = txn.get('payee') or txn.get('description') or 'Unknown Transaction'
                    category = 'Other'
                    
                    if amount > 0:
                        # Income
                        new_income = Income(
                            user_id=current_user_id,
                            amount=amount,
                            source=description,
                            date=txn_date,
                            simplefin_id=txn_id
                        )
                        db.session.add(new_income)
                        synced_count += 1
                        
                    elif amount < 0:
                        # Expense
                        # Apply smart categorization
                        from utils import auto_categorize
                        mapped_category = auto_categorize(description, current_user_id)
                        
                        new_expense = Expense(
                            user_id=current_user_id,
                            amount=abs(amount),
                            category=mapped_category, # Use our smart categorization
                            description=description,
                            date=txn_date,
                            simplefin_id=txn_id
                        )
                        db.session.add(new_expense)
                        synced_count += 1
            
            db.session.commit()
            current_app.logger.info(f"[SimpleFin] Synced {synced_count} new transactions")
            
            return jsonify({
                'message': 'Sync successful',
                'accounts': accounts,
                'new_transactions': synced_count,
                'errors': data.get('errors', [])
            }), 200
        else:
            return jsonify({
                'message': 'Failed to sync',
                'status': response.status_code,
                'details': response.text[:500] if response.text else 'No details'
            }), response.status_code
            
    except Exception as e:
        current_app.logger.error(f"[SimpleFin] Sync error: {str(e)}")
        db.session.rollback()
        return jsonify({'message': 'Sync error', 'error': str(e)}), 500

@simplefin_bp.route('/accounts', methods=['GET'])
@token_required
def get_accounts(current_user_id):
    """
    Get accounts from SimpleFin (same as sync)
    ---
    security:
      - Bearer: []
    responses:
      200:
        description: List of accounts
    """
    user = User.query.get(current_user_id)
    
    # Try DB token first, then Env var
    access_url = None
    if user and user.simplefin_token:
        access_url = decrypt_token(user.simplefin_token)
    elif os.environ.get('SIMPLEFIN_TOKEN'):
        access_url = os.environ.get('SIMPLEFIN_TOKEN')

    if not access_url:
        return jsonify({'message': 'SimpleFin not connected'}), 401
    
    try:
        response = requests.get(f"{access_url}/accounts", timeout=30)
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({'message': 'Failed to fetch accounts', 'status': response.status_code}), response.status_code
    except Exception as e:
        return jsonify({'message': 'Error', 'error': str(e)}), 500
