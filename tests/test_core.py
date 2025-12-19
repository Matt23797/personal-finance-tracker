import unittest
from app import create_app
from models import db, User

class TestCore(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            # Register a test user
            from werkzeug.security import generate_password_hash
            self.user = User(username='testuser', password_hash=generate_password_hash('pass123'))
            db.session.add(self.user)
            db.session.commit()
            self.user_id = self.user.id

        # Login to get token
        resp = self.client.post('/auth/login', json={"username": "testuser", "password": "pass123"})
        self.token = resp.get_json().get('token')
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_add_get_income(self):
        income_data = {
            "amount": 1000.50,
            "source": "Salary",
            "date": "2023-10-27"
        }
        resp = self.client.post('/api/incomes', json=income_data, headers=self.headers)
        self.assertEqual(resp.status_code, 201)

        resp = self.client.get('/api/incomes', headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(len(data) >= 1)
        self.assertEqual(data[-1]['amount'], 1000.50)

    def test_add_get_expense(self):
        expense_data = {
            "amount": 50.25,
            "category": "Food",
            "date": "2023-10-28"
        }
        resp = self.client.post('/api/expenses', json=expense_data, headers=self.headers)
        self.assertEqual(resp.status_code, 201)

        resp = self.client.get('/api/expenses', headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(len(data) >= 1)
        self.assertEqual(data[-1]['amount'], 50.25)
    
    def test_summary(self):
        self.client.post('/api/incomes', json={"amount": 200, "source": "test", "date": "2023-01-01"}, headers=self.headers)
        self.client.post('/api/expenses', json={"amount": 50, "category": "test", "date": "2023-01-01"}, headers=self.headers)

        resp = self.client.get('/api/summary', headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('total_income', data)
        self.assertIn('total_expense', data)

if __name__ == '__main__':
    unittest.main()
