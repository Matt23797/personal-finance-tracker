import unittest
import json
from app import create_app
from models import db, User, Income, Expense, Budget
from datetime import datetime, timedelta

class TestForecast(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self.user = User(username='testuser', password_hash='hash')
            db.session.add(self.user)
            db.session.commit()
            self.user_id = self.user.id
            
            # Create a token for the user
            import jwt
            import os
            self.token = jwt.encode(
                {'user_id': self.user_id, 'exp': datetime.utcnow() + timedelta(hours=1)},
                os.environ.get('SECRET_KEY', 'dev_key'),
                algorithm='HS256'
            )

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_forecast_calculation(self):
        with self.app.app_context():
            # Add some history
            today = datetime.utcnow().date()
            # Total Income: 1000
            db.session.add(Income(user_id=self.user_id, amount=1000, source='Job', date=today - timedelta(days=10)))
            # Total Expense: 400 (Daily burn roughly 400/60 = 6.67)
            db.session.add(Expense(user_id=self.user_id, amount=400, category='Rent', date=today - timedelta(days=5)))
            db.session.commit()

        response = self.client.get('/api/forecast', headers={'Authorization': f'Bearer {self.token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Balance should be 600
        self.assertEqual(data['current_balance'], 600.0)
        # 91 points in projection
        self.assertEqual(len(data['projection']), 91)
        # First point should match current balance
        self.assertEqual(data['projection'][0]['balance'], 600.0)

if __name__ == '__main__':
    unittest.main()
