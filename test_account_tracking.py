
import os
import shutil
import unittest
import csv
import io
import json
from app import create_app
from models import db, Income, Expense, Account
from decimal import Decimal
from datetime import datetime, timedelta

class TestAccountTracking(unittest.TestCase):

    def setUp(self):
        self.test_instance_path = os.path.abspath('test_instance')
        if os.path.exists(self.test_instance_path):
            shutil.rmtree(self.test_instance_path)
        os.makedirs(self.test_instance_path)
        
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test_key',
            'INSTANCE_PATH': self.test_instance_path
        })
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        self.client = self.app.test_client()
        
        # User
        from models import User
        user = User(username='test', password_hash='hash')
        db.session.add(user)
        db.session.commit()
        self.user_id = user.id
        
        # Token
        import jwt
        self.token = jwt.encode(
            {'user_id': self.user_id, 'exp': datetime.utcnow() + timedelta(hours=1)}, 
            self.app.config['SECRET_KEY'], 
            algorithm='HS256'
        )
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        if os.path.exists(self.test_instance_path):
            shutil.rmtree(self.test_instance_path)

    def test_manual_account_lifecycle(self):
        """Test creating, listing, and updating a manual account"""
        # Create
        res = self.client.post('/api/accounts', headers=self.headers, json={
            'name': 'Wallet',
            'balance': 500.00,
            'type': 'cash'
        })
        self.assertEqual(res.status_code, 201)
        acc_id = res.get_json()['id']
        
        # List
        res = self.client.get('/api/accounts', headers=self.headers)
        data = res.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Wallet')
        self.assertEqual(data[0]['balance'], 500.0)
        
        # Update
        res = self.client.put(f'/api/accounts/{acc_id}', headers=self.headers, json={
            'balance': 450.00
        })
        self.assertEqual(res.status_code, 200)
        
        # Verify in DB
        acc = Account.query.get(acc_id)
        self.assertEqual(acc.balance, Decimal('450.00'))

    def test_import_to_account(self):
        """Test importing CSV transactions into a specific account"""
        # Create Account
        acc = Account(user_id=self.user_id, name='Bank', balance=1000)
        db.session.add(acc)
        db.session.commit()
        
        # CSV Content
        csv_content = "Date,Description,Amount\n2025-01-01,Test Income,100.00"
        
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'account_id': str(acc.id)
        }
        
        res = self.client.post('/api/transactions/import', headers=self.headers, content_type='multipart/form-data', data=data)
        self.assertEqual(res.status_code, 200)
        
        # Verify Transaction Linked
        inc = Income.query.first()
        self.assertIsNotNone(inc)
        self.assertEqual(inc.account_id, acc.id)
        self.assertEqual(inc.amount, Decimal('100.00'))

    def test_forecast_uses_account_balance(self):
        """Verify forecast starts from sum of account balances"""
        # Create 2 accounts
        db.session.add(Account(user_id=self.user_id, name='A1', balance=100))
        db.session.add(Account(user_id=self.user_id, name='A2', balance=500))
        db.session.commit()
        
        res = self.client.get('/api/forecast', headers=self.headers)
        data = res.get_json()
        
        # 100 + 500 = 600
        self.assertEqual(data['current_balance'], 600.0)

if __name__ == '__main__':
    unittest.main()
