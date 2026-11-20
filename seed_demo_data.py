"""
SpendWise Demo Seeder
Seeds realistic multi-month data for rich visualization and instant testing.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expense_tracker.db')

def seed():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    demo_email = 'demo@spendwise.com'
    demo_password = 'Password@123'
    demo_name = 'Alex Morgan'

    # Check if demo user already exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (demo_email,))
    existing = cursor.fetchone()
    if existing:
        user_id = existing[0]
        # Clean existing transactions for fresh demo state
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM budgets WHERE user_id = ?", (user_id,))
    else:
        pwd_hash = generate_password_hash(demo_password)
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, status)
            VALUES (?, ?, ?, 'user', 'active')
        """, (demo_name, demo_email, pwd_hash))
        user_id = cursor.lastrowid

    # Record login
    cursor.execute("INSERT INTO logins (user_id) VALUES (?)", (user_id,))

    # Transactions dataset across current year (2026)
    year = 2026
    sample_transactions = [
        # January
        ('income', 'Salary', 85000.00, 'January Monthly Salary', f'{year}-01-01'),
        ('expense', 'Bills', 4500.00, 'Apartment Maintenance & Utilities', f'{year}-01-05'),
        ('expense', 'Food', 6200.00, 'Monthly Supermarket Grocery Haul', f'{year}-01-10'),
        ('expense', 'Shopping', 3500.00, 'Winter Clothing Sale', f'{year}-01-15'),
        ('expense', 'Health', 1200.00, 'Annual Health Checkup', f'{year}-01-22'),

        # February
        ('income', 'Salary', 85000.00, 'February Monthly Salary', f'{year}-02-01'),
        ('income', 'Freelance', 18000.00, 'UI Design Project for Client', f'{year}-02-14'),
        ('expense', 'Bills', 3200.00, 'Electricity & Broadband Bill', f'{year}-02-06'),
        ('expense', 'Food', 5800.00, 'Groceries & Provisions', f'{year}-02-12'),
        ('expense', 'Travel', 4200.00, 'Weekend Mountain Trip Fuel & Stay', f'{year}-02-20'),

        # March
        ('income', 'Salary', 85000.00, 'March Monthly Salary', f'{year}-03-01'),
        ('expense', 'Bills', 3100.00, 'Utility Bills', f'{year}-03-07'),
        ('expense', 'Food', 6400.00, 'Organic Groceries', f'{year}-03-12'),
        ('expense', 'Education', 4500.00, 'Fullstack Web Dev Certification', f'{year}-03-18'),

        # April
        ('income', 'Salary', 85000.00, 'April Monthly Salary', f'{year}-04-01'),
        ('income', 'Gift', 5000.00, 'Birthday Gift from Family', f'{year}-04-10'),
        ('expense', 'Shopping', 7200.00, 'Ergonomic Desk Chair', f'{year}-04-12'),
        ('expense', 'Food', 5900.00, 'Weekly Grocery Orders', f'{year}-04-16'),
        ('expense', 'Bills', 3400.00, 'Electricity & Gas Bill', f'{year}-04-25'),

        # May
        ('income', 'Salary', 85000.00, 'May Monthly Salary', f'{year}-05-01'),
        ('expense', 'Food', 6100.00, 'Groceries & Dining Out', f'{year}-05-08'),
        ('expense', 'Travel', 6500.00, 'Flight Booking for Vacation', f'{year}-05-15'),
        ('expense', 'Bills', 3300.00, 'Broadband & Mobile Bills', f'{year}-05-22'),

        # June
        ('income', 'Salary', 85000.00, 'June Monthly Salary', f'{year}-06-01'),
        ('income', 'Freelance', 22000.00, 'Mobile App Consultation', f'{year}-06-12'),
        ('expense', 'Food', 5400.00, 'Supermarket Supplies', f'{year}-06-09'),
        ('expense', 'Bills', 3600.00, 'Summer Power Bill', f'{year}-06-20'),
        ('expense', 'Health', 2400.00, 'Dental Care & Cleaning', f'{year}-06-24'),

        # July
        ('income', 'Salary', 85000.00, 'July Monthly Salary', f'{year}-07-01'),
        ('expense', 'Food', 6300.00, 'Monthly Groceries', f'{year}-07-07'),
        ('expense', 'Shopping', 4100.00, 'Running Shoes & Sports Gear', f'{year}-07-14'),
        ('expense', 'Bills', 3200.00, 'Water & Electricity', f'{year}-07-21'),

        # August
        ('income', 'Salary', 85000.00, 'August Monthly Salary', f'{year}-08-01'),
        ('expense', 'Food', 5700.00, 'Pantry Staples & Vegetables', f'{year}-08-05'),
        ('expense', 'Education', 3500.00, 'Technical Architecture Books', f'{year}-08-16'),
        ('expense', 'Travel', 2800.00, 'Express Train Travel', f'{year}-08-25'),

        # September
        ('income', 'Salary', 85000.00, 'September Monthly Salary', f'{year}-09-01'),
        ('income', 'Business', 14000.00, 'Digital Product Sales', f'{year}-09-15'),
        ('expense', 'Food', 6600.00, 'Groceries and Cafe Meetups', f'{year}-09-08'),
        ('expense', 'Bills', 3100.00, 'High-Speed Fiber Bill', f'{year}-09-20'),

        # October
        ('income', 'Salary', 85000.00, 'October Monthly Salary', f'{year}-10-01'),
        ('expense', 'Food', 6800.00, 'Festival Groceries & Sweets', f'{year}-10-10'),
        ('expense', 'Shopping', 8500.00, 'Festive Home Decor & Lighting', f'{year}-10-18'),
        ('expense', 'Bills', 3400.00, 'Monthly Utility Bills', f'{year}-10-24'),

        # November (Current active month)
        ('income', 'Salary', 85000.00, 'November Monthly Salary', f'{year}-11-01'),
        ('expense', 'Bills', 3500.00, 'Electricity and Water Utility Bill', f'{year}-11-04'),
        ('expense', 'Food', 4200.00, 'Weekly Organic Market Groceries', f'{year}-11-08'),
        ('expense', 'Shopping', 2800.00, 'Wireless Noise-Cancelling Headphones', f'{year}-11-12'),
        ('expense', 'Travel', 1850.00, 'Cab & Public Commute', f'{year}-11-15'),
        ('expense', 'Health', 1400.00, 'Supplements & Multi-vitamins', f'{year}-11-18'),
        ('expense', 'Food', 1650.00, 'Dinner at Olive Bistro', f'{year}-11-20'),
    ]

    for tx_type, category, amount, description, date_str in sample_transactions:
        cursor.execute("""
            INSERT INTO transactions (user_id, type, category, amount, description, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, tx_type, category, amount, description, date_str))

    # Seed Budgets
    sample_budgets = [
        ('Food', 12000.00),
        ('Shopping', 8000.00),
        ('Bills', 5000.00),
        ('Travel', 6000.00),
        ('Health', 4000.00)
    ]

    for cat, limit in sample_budgets:
        cursor.execute("""
            INSERT OR REPLACE INTO budgets (user_id, category, monthly_limit)
            VALUES (?, ?, ?)
        """, (user_id, cat, limit))

    conn.commit()
    conn.close()
    print(f"[SpendWise] Successfully seeded demo user '{demo_email}' with {len(sample_transactions)} transactions!")

if __name__ == '__main__':
    seed()
