from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index():
    return render_template('index.html')

@pages_bp.route('/login')
def login():
    return render_template('login.html')

@pages_bp.route('/transactions')
def transactions():
    return render_template('transactions.html')

@pages_bp.route('/goals')
def goals():
    return render_template('goals.html')

@pages_bp.route('/settings')
def settings():
    return render_template('settings.html')
    
@pages_bp.route('/budget')
def budget_page():
    return render_template('budget.html')

@pages_bp.route('/forecast')
def forecast_page():
    return render_template('forecast.html')
