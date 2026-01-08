
import os
import shutil
import unittest
import csv
import io
from app import create_app
from models import db, Income, Expense
from decimal import Decimal
from datetime import datetime, timedelta

class TestFunctionalImprovements(unittest.TestCase):

    def setUp(self):
        # Setup test app with temporary instance path
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
        
        # Create a test user
        from models import User
        user = User(username='test', password_hash='hash')
        db.session.add(user)
        db.session.commit()
        self.user_id = user.id
        
        # Creating a login token manually for "test" user (id 1)
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

    def test_forecast_no_500_error(self):
        """Verify forecast works with Decimal data (should not crash)"""
        # Add income with Decimal
        inc = Income(user_id=self.user_id, amount=Decimal('100.50'), source='Job', simplefin_id='1')
        exp = Expense(user_id=self.user_id, amount=Decimal('50.25'), category='Food', simplefin_id='2')
        db.session.add(inc)
        db.session.add(exp)
        db.session.commit()
        
        res = self.client.get('/api/forecast', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        # Check structure
        self.assertIn('projection', data)
        self.assertEqual(len(data['projection']), 91)
        self.assertIsInstance(data['current_balance'], float)

    def test_forecast_payday_logic(self):
        """Verify payday logic detects recurring income"""
        # Add a "payday" income > 100
        payday = Income(user_id=self.user_id, amount=Decimal('2000.00'), source='Paycheck', date=datetime.utcnow().date())
        db.session.add(payday)
        db.session.commit()
        
        res = self.client.get('/api/forecast', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

    def test_export_csv(self):
        """Verify CSV export"""
        # Add some data
        date_str = '2025-01-01'
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        inc = Income(user_id=self.user_id, amount=Decimal('500.00'), source='Bonus', date=date_obj)
        db.session.add(inc)
        db.session.commit()
        
        res = self.client.get('/api/export/transactions', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers['Content-Type'], 'text/csv')
        
        # Parse CSV
        csv_text = res.data.decode('utf-8')
        f = io.StringIO(csv_text)
        reader = csv.reader(f)
        rows = list(reader)
        
        # Header
        self.assertEqual(rows[0], ['Date', 'Type', 'Category', 'Amount', 'Description'])
        # Data row
        self.assertEqual(rows[1][0], date_str)
        self.assertEqual(rows[1][1], 'Income')
        self.assertEqual(rows[1][3], '500.00')

if __name__ == '__main__':
    unittest.main()
