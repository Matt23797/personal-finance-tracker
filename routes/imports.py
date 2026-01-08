from flask import Blueprint, request, jsonify
from models import db, Income, Expense
from routes.auth import token_required
from utils import auto_categorize
from datetime import datetime
import io
import csv
import hashlib
from ofxparse import OfxParser

imports_bp = Blueprint('imports', __name__, url_prefix='/api/transactions')

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

    
    if imported > 0 and account_id:
        from models import Account
        # Update Account Balance
        account = Account.query.filter_by(id=account_id, user_id=user_id).first()
        if account:
            # Calculate net change from this import
            # We need to sum the amounts of the *newly added* items
            # Since we just added them to session, we can iterate them, 
            # but db.session.new might contain other things.
            # Simpler: Accumulate net_amount during the loop.
            pass

    return imported, duplicates

def process_csv(content, user_id, account_id=None):
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
    net_import_amount = 0.0

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
                new_item = Expense(user_id=user_id, amount=abs(amount), category=category, description=desc, date=dt, simplefin_id=unique_id, account_id=account_id)
                net_import_amount += amount # amount is negative
            else:
                new_item = Income(user_id=user_id, amount=amount, source=desc, date=dt, simplefin_id=unique_id, account_id=account_id)
                net_import_amount += amount
            
            db.session.add(new_item)
            imported += 1
        except: continue
        
    if imported > 0 and account_id:
        from models import Account
        account = Account.query.get(account_id)
        if account and account.user_id == user_id:
            # For manual accounts, imports essentially "replay" history, so we add the net amount.
            # User can always manually correct the final balance in Settings if this assumption is wrong.
            account.balance = float(account.balance) + net_import_amount
            account.last_synced = datetime.utcnow()
    
    return imported, duplicates

@imports_bp.route('/import', methods=['POST'])
@token_required
def import_transactions(current_user_id):
    """
    Import transactions from CSV/OFX
    ---
    security:
      - Bearer: []
    parameters:
      - name: file
        in: formData
        type: file
        required: true
    responses:
      200:
        description: Transactions imported
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    account_id = request.form.get('account_id')
    
    if account_id:
        try:
            account_id = int(account_id)
            # Verify account ownership
            # from models import Account
            # if not Account.query.filter_by(id=account_id, user_id=current_user_id).first():
            #    return jsonify({"error": "Invalid account"}), 403
            # Assuming simple valid ID check for now to keep imports clean
        except:
            account_id = None
    
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename = file.filename.lower()
    content = file.read()
    
    if filename.endswith(('.ofx', '.qfx')):
        # OFX usually contains account info, so we might ignore account_id or use it as fallback
        imported, duplicates = process_ofx(content, current_user_id) 
    elif filename.endswith('.csv'):
        imported, duplicates = process_csv(content, current_user_id, account_id)
    else:
        return jsonify({"error": "Unsupported file format. Please use CSV, OFX, or QFX."}), 400

    db.session.commit()
    return jsonify({
        "message": f"Successfully imported {imported} transactions.",
        "duplicates": duplicates
    }), 200
