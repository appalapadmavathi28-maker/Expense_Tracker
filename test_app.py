"""
SpendWise Automated Test Suite
Verifies all core requirements, edge cases, security controls, and user isolation.
"""

import unittest
import json
import os
import sqlite3
import app as app_module
from app import app, init_db

class SpendWiseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure isolated test database
        cls.test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_expense_tracker.db')
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
        app_module.DATABASE = cls.test_db
        init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db):
            try:
                os.remove(cls.test_db)
            except Exception:
                pass

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_user_registration_validation(self):
        # Name too short
        res = self.client.post('/register', json={
            'name': 'A',
            'email': 'short@example.com',
            'password': 'Password123'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('at least 2 characters', res.get_json()['message'])

        # Invalid email
        res = self.client.post('/register', json={
            'name': 'Valid Name',
            'email': 'not-an-email',
            'password': 'Password123'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('valid email', res.get_json()['message'])

        # Weak password (no number)
        res = self.client.post('/register', json={
            'name': 'Valid Name',
            'email': 'valid@example.com',
            'password': 'JustLetters'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('at least 8 characters', res.get_json()['message'])

        # Weak password (less than 8 chars)
        res = self.client.post('/register', json={
            'name': 'Valid Name',
            'email': 'valid@example.com',
            'password': 'Pass1'
        })
        self.assertEqual(res.status_code, 400)

        # Successful registration
        res = self.client.post('/register', json={
            'name': 'John Doe',
            'email': 'johndoe@example.com',
            'password': 'StrongPassword123'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

        # Duplicate email registration
        res = self.client.post('/register', json={
            'name': 'John Duplicate',
            'email': 'johndoe@example.com',
            'password': 'StrongPassword123'
        })
        self.assertEqual(res.status_code, 409)

    def test_02_authentication_and_session(self):
        # Invalid login
        res = self.client.post('/login', json={
            'email': 'johndoe@example.com',
            'password': 'WrongPassword123'
        })
        self.assertEqual(res.status_code, 401)

        # Successful login
        res = self.client.post('/login', json={
            'email': 'johndoe@example.com',
            'password': 'StrongPassword123'
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

        # Access protected endpoint /api/me
        res = self.client.get('/api/me')
        self.assertEqual(res.status_code, 200)
        user_info = res.get_json()['user']
        self.assertEqual(user_info['email'], 'johndoe@example.com')

        # Logout
        res = self.client.get('/logout')
        self.assertEqual(res.status_code, 302)

        # Verify access without session is now 401
        res = self.client.get('/api/me')
        self.assertEqual(res.status_code, 401)

    def test_03_transaction_crud_and_validation(self):
        # Login first
        self.client.post('/login', json={
            'email': 'johndoe@example.com',
            'password': 'StrongPassword123'
        })

        # Test invalid amount (<= 0)
        res = self.client.post('/api/transactions', json={
            'type': 'expense',
            'category': 'Food',
            'amount': 0,
            'description': 'Free meal',
            'date': '2026-11-20'
        })
        self.assertEqual(res.status_code, 400)

        # Test invalid category for expense
        res = self.client.post('/api/transactions', json={
            'type': 'expense',
            'category': 'Salary',  # Salary is income category
            'amount': 500,
            'description': 'Salary as expense',
            'date': '2026-11-20'
        })
        self.assertEqual(res.status_code, 400)

        # Test missing description
        res = self.client.post('/api/transactions', json={
            'type': 'expense',
            'category': 'Food',
            'amount': 250,
            'description': '',
            'date': '2026-11-20'
        })
        self.assertEqual(res.status_code, 400)

        # Add valid expense
        res = self.client.post('/api/transactions', json={
            'type': 'expense',
            'category': 'Food',
            'amount': 450.50,
            'description': 'Dinner at Olive Bistro',
            'date': '2026-11-20'
        })
        self.assertEqual(res.status_code, 201)
        tx1_id = res.get_json()['id']

        # Add valid income
        res = self.client.post('/api/transactions', json={
            'type': 'income',
            'category': 'Salary',
            'amount': 75000.00,
            'description': 'Monthly Software Engineering Salary',
            'date': '2026-11-01'
        })
        self.assertEqual(res.status_code, 201)
        tx2_id = res.get_json()['id']

        # Add transaction with formula injection test
        res = self.client.post('/api/transactions', json={
            'type': 'expense',
            'category': 'Bills',
            'amount': 1200.00,
            'description': '=SUM(A1:A10)',
            'date': '2026-11-15'
        })
        self.assertEqual(res.status_code, 201)
        tx3_id = res.get_json()['id']

        # Read transactions
        res = self.client.get('/api/transactions')
        self.assertEqual(res.status_code, 200)
        tx_list = res.get_json()['transactions']
        self.assertGreaterEqual(len(tx_list), 3)

        # Update transaction tx1
        res = self.client.put(f'/api/transactions/{tx1_id}', json={
            'type': 'expense',
            'category': 'Food',
            'amount': 500.00,
            'description': 'Dinner at Olive Bistro (Updated)',
            'date': '2026-11-20'
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

        # Delete transaction tx3
        res = self.client.delete(f'/api/transactions/{tx3_id}')
        self.assertEqual(res.status_code, 200)

        # Verify tx3 is gone
        res = self.client.get('/api/transactions')
        ids = [t['id'] for t in res.get_json()['transactions']]
        self.assertNotIn(tx3_id, ids)

    def test_04_user_isolation(self):
        # Register User 2
        self.client.post('/register', json={
            'name': 'Jane Smith',
            'email': 'janesmith@example.com',
            'password': 'StrongPassword456'
        })

        # Add transaction as User 2
        res = self.client.post('/api/transactions', json={
            'type': 'expense',
            'category': 'Shopping',
            'amount': 1999.00,
            'description': 'Jane Private Sneakers Purchase',
            'date': '2026-11-18'
        })
        jane_tx_id = res.get_json()['id']

        # Now login back as User 1 (John)
        self.client.post('/login', json={
            'email': 'johndoe@example.com',
            'password': 'StrongPassword123'
        })

        # John lists transactions: Jane's transaction MUST NOT appear
        res = self.client.get('/api/transactions')
        john_tx_ids = [t['id'] for t in res.get_json()['transactions']]
        self.assertNotIn(jane_tx_id, john_tx_ids)

        # John tries to update Jane's transaction
        res = self.client.put(f'/api/transactions/{jane_tx_id}', json={
            'type': 'expense',
            'category': 'Shopping',
            'amount': 1.00,
            'description': 'Hacked by John',
            'date': '2026-11-18'
        })
        self.assertEqual(res.status_code, 404)

        # John tries to delete Jane's transaction
        res = self.client.delete(f'/api/transactions/{jane_tx_id}')
        self.assertEqual(res.status_code, 404)

    def test_05_reports_and_budgets(self):
        # Login as John
        self.client.post('/login', json={
            'email': 'johndoe@example.com',
            'password': 'StrongPassword123'
        })

        # Monthly report
        res = self.client.get('/api/reports/monthly?year=2026&month=11')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['year'], 2026)
        self.assertEqual(data['selected_month'], 11)
        self.assertEqual(len(data['twelve_months_data']), 12)

        # Set Category Budget
        res = self.client.post('/api/budgets', json={
            'category': 'Food',
            'monthly_limit': 10000.00
        })
        self.assertEqual(res.status_code, 200)

        # Get budgets
        res = self.client.get('/api/budgets')
        self.assertEqual(res.status_code, 200)
        budgets = res.get_json()['budgets']
        self.assertTrue(any(b['category'] == 'Food' for b in budgets))

    def test_06_csv_export_injection_protection(self):
        # Login as John
        self.client.post('/login', json={
            'email': 'johndoe@example.com',
            'password': 'StrongPassword123'
        })

        # Add transaction with dangerous formula characters
        self.client.post('/api/transactions', json={
            'type': 'expense',
            'category': 'Other',
            'amount': 99.00,
            'description': '=1+1',
            'date': '2026-11-19'
        })

        res = self.client.get('/api/transactions/export')
        self.assertEqual(res.status_code, 200)
        csv_text = res.get_data(as_text=True)
        # Verify that the cell starts with '=1+1 is escaped as '=1+1
        self.assertIn("'=1+1", csv_text)

    def test_07_admin_dashboard_security(self):
        # Attempt to access admin API as regular user John
        res = self.client.get('/api/admin/stats')
        self.assertEqual(res.status_code, 403)

        # Admin login with default credentials
        res = self.client.post('/admin/login', json={
            'email': 'admin@expense.com',
            'password': 'Admin@123'
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

        # Admin stats
        res = self.client.get('/api/admin/stats')
        self.assertEqual(res.status_code, 200)
        stats = res.get_json()
        self.assertGreaterEqual(stats['total_users'], 2)
        self.assertGreaterEqual(stats['total_logins'], 1)
        self.assertIn('logins_7_days', stats)
        self.assertIn('recent_activity', stats)

        # Admin users directory: MUST NOT contain password_hash
        res = self.client.get('/api/admin/users')
        self.assertEqual(res.status_code, 200)
        users = res.get_json()['users']
        for u in users:
            self.assertNotIn('password_hash', u)
            self.assertIn('email', u)
            self.assertIn('transaction_count', u)

        # Test toggle user status (Disable Jane)
        jane_user = next(u for u in users if u['email'] == 'janesmith@example.com')
        res = self.client.post(f'/api/admin/users/{jane_user["id"]}/status', json={'status': 'disabled'})
        self.assertEqual(res.status_code, 200)

        # Try to login as disabled Jane
        res = self.client.post('/login', json={
            'email': 'janesmith@example.com',
            'password': 'StrongPassword456'
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn('disabled', res.get_json()['message'])

        # Re-enable Jane
        res = self.client.post(f'/api/admin/users/{jane_user["id"]}/status', json={'status': 'active'})
        self.assertEqual(res.status_code, 200)

        # Jane can log in now
        res = self.client.post('/login', json={
            'email': 'janesmith@example.com',
            'password': 'StrongPassword456'
        })
        self.assertEqual(res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
