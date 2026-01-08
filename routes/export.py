import io
import csv
from flask import Blueprint, make_response, request
from models import Income, Expense
from routes.auth import token_required

export_bp = Blueprint('export', __name__, url_prefix='/api/export')

@export_bp.route('/transactions', methods=['GET'])
@token_required
def export_transactions(current_user_id):
    """
    Export all transactions (income and expenses) to CSV
    """
    incomes = Income.query.filter_by(user_id=current_user_id).order_by(Income.date.desc()).all()
    expenses = Expense.query.filter_by(user_id=current_user_id).order_by(Expense.date.desc()).all()
    
    # Combine and sort
    all_txns = []
    
    for inc in incomes:
        all_txns.append({
            'date': inc.date,
            'type': 'Income',
            'amount': inc.amount,
            'category': 'Income',
            'description': inc.source
        })
        
    for exp in expenses:
        all_txns.append({
            'date': exp.date,
            'type': 'Expense',
            'amount': -exp.amount,
            'category': exp.category,
            'description': exp.description or ''
        })
        
    all_txns.sort(key=lambda x: x['date'], reverse=True)
    
    # Generate CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Type', 'Category', 'Amount', 'Description'])
    
    for txn in all_txns:
        cw.writerow([
            txn['date'].strftime('%Y-%m-%d'),
            txn['type'],
            txn['category'],
            f"{txn['amount']:.2f}",
            txn['description']
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=finance_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output
