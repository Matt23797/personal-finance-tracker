from flask import Flask, render_template, jsonify
from models import db
from flasgger import Swagger
from routes.auth import auth_bp
from routes.transactions import transactions_bp
from routes.simplefin import simplefin_bp
from routes.pages import pages_bp
from routes.goals import goals_bp
from routes.categories import categories_bp
from routes.imports import imports_bp
from routes.forecasts import forecasts_bp
from routes.budget import budget_bp

import os
import sys
import webbrowser
import threading
import time
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()


def create_app(test_config=None):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        template_folder = os.path.join(base_path, 'templates')
        static_folder = os.path.join(base_path, 'static')
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(__name__)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key')

    if test_config:
        app.config.update(test_config)
    else:
        if getattr(sys, 'frozen', False):
            # Path where the .exe is located
            app_dir = os.path.dirname(sys.executable)
            db_path = os.path.join(app_dir, 'finance.db')
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
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

    # Register Blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(simplefin_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(forecasts_bp)
    app.register_blueprint(budget_bp)

    with app.app_context():
        db.create_all()

    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy", "database": "connected"}), 200

    return app


def open_browser():
    """Wait for server to start and then open browser."""
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    app = create_app()
    if getattr(sys, 'frozen', False):
        threading.Thread(target=open_browser).start()
    app.run(port=5000)
