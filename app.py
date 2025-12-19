from flask import Flask, render_template, jsonify
from models import db
from flasgger import Swagger
from routes.auth import auth_bp
from routes.main import main_bp
from routes.simplefin import simplefin_bp
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key')

    if test_config:
        app.config.update(test_config)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'

    db.init_app(app)
    Swagger(app)

    # Configure Production Logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/finance_tracker.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Finance Tracker startup')

    app.register_blueprint(auth_bp)

    app.register_blueprint(main_bp)
    app.register_blueprint(simplefin_bp)

    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login')
    def login():
        return render_template('login.html')

    @app.route('/transactions')
    def transactions():
        return render_template('transactions.html')

    @app.route('/goals')
    def goals():
        return render_template('goals.html')

    @app.route('/settings')
    def settings():
        return render_template('settings.html')
        
    @app.route('/budget')
    def budget_page():
        return render_template('budget.html')

    @app.route('/forecast')
    def forecast_page():
        return render_template('forecast.html')

    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy", "database": "connected"}), 200

    return app


if __name__ == '__main__':
    app = create_app()
    app.run()
