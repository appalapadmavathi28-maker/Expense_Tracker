"""
SpendWise - Smart Expense Tracker
A complete, production-grade Flask web application with SQLite database integration.
"""

import os
import re
import csv
import io
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify, redirect, url_for,
    session, g, make_response
)
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# FLASK APPLICATION CONFIGURATION
# ==============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'spendwise-production-secret-key-3f98c21a0')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expense_tracker.db')

DEFAULT_ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@expense.com')
DEFAULT_ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin@123')

# Valid Categories
EXPENSE_CATEGORIES = {'Food', 'Shopping', 'Travel', 'Education', 'Bills', 'Health', 'Other'}
INCOME_CATEGORIES = {'Salary', 'Freelance', 'Business', 'Gift', 'Other'}
ALL_CATEGORIES = EXPENSE_CATEGORIES.union(INCOME_CATEGORIES)


# ==============================================================================
# DATABASE UTILITIES
# ==============================================================================

def get_db():
    """Returns a thread-local SQLite connection with Row factory and foreign keys enabled."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Closes the database connection at the end of the request context."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initializes SQLite database tables and seeds the default admin user."""
    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # Logins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # Category Budgets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL CHECK(monthly_limit > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # Required Index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_user_date
            ON transactions(user_id, date);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_logins_user_ts
            ON logins(user_id, ts);
        """)

        # Seed Default Administrator if not already present
        cursor.execute("SELECT id FROM users WHERE email = ?", (DEFAULT_ADMIN_EMAIL.lower(),))
        admin = cursor.fetchone()
        if not admin:
            admin_pwd_hash = generate_password_hash(DEFAULT_ADMIN_PASSWORD)
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role, status)
                VALUES (?, ?, ?, 'admin', 'active')
            """, ('System Administrator', DEFAULT_ADMIN_EMAIL.lower(), admin_pwd_hash))
            conn.commit()
            print(f"[SpendWise] Initialized DB and seeded default admin: {DEFAULT_ADMIN_EMAIL}")
    finally:
        conn.close()


# ==============================================================================
# AUTHENTICATION & AUTHORIZATION DECORATORS
# ==============================================================================

def login_required(f):
    """Requires active user session. Redirects browser requests to /login, returns 401 for API."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            return redirect(url_for('login'))

        # Verify user still exists and account is active
        db = get_db()
        user = db.execute("SELECT id, status FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user or user['status'] != 'active':
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Account disabled or invalid'}), 401
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Requires admin session role. Redirects browser requests to /admin/login, returns 403 for API."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        role = session.get('role')

        if not user_id or role != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Administrator access required'}), 403
            return redirect(url_for('admin_login'))

        db = get_db()
        user = db.execute("SELECT id, role, status FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user or user['role'] != 'admin' or user['status'] != 'active':
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Unauthorized admin'}), 403
            return redirect(url_for('admin_login'))

        return f(*args, **kwargs)
    return decorated_function


def sanitize_csv_value(val):
    """Protects against CSV Formula Injection by prefixing unsafe characters with a quote."""
    if val is None:
        return ""
    text = str(val)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text


# ==============================================================================
# AUTHENTICATION ROUTES
# ==============================================================================

@app.route('/')
def index():
    """Root route: redirects logged-in users to /app, admins to /admin, others to /login."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('user_dashboard'))
        return render_template('login.html')

    # Handle POST
    data = request.get_json(silent=True) or request.form
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400

    db = get_db()
    user = db.execute(
        "SELECT id, name, email, password_hash, role, status FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

    if user['status'] != 'active':
        return jsonify({'success': False, 'message': 'This account has been disabled. Contact admin.'}), 403

    # Successful login: record login event & set session
    db.execute("INSERT INTO logins (user_id) VALUES (?)", (user['id'],))
    db.commit()

    session.permanent = True
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['role'] = user['role']

    target_redirect = url_for('admin_dashboard') if user['role'] == 'admin' else url_for('user_dashboard')
    return jsonify({'success': True, 'redirect': target_redirect})


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('user_dashboard'))
        return render_template('register.html')

    # Handle POST
    data = request.get_json(silent=True) or request.form
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    # Server-side validation
    if len(name) < 2:
        return jsonify({'success': False, 'message': 'Name must be at least 2 characters long'}), 400

    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_pattern, email):
        return jsonify({'success': False, 'message': 'Please provide a valid email address'}), 400

    if len(password) < 8 or not re.search(r'[a-zA-Z]', password) or not re.search(r'[0-9]', password):
        return jsonify({
            'success': False,
            'message': 'Password must be at least 8 characters long and contain both letters and numbers'
        }), 400

    db = get_db()
    existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing_user:
        return jsonify({'success': False, 'message': 'An account with this email already exists'}), 409

    pwd_hash = generate_password_hash(password)
    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash, role, status) VALUES (?, ?, ?, 'user', 'active')",
        (name, email, pwd_hash)
    )
    new_user_id = cursor.lastrowid

    # Record initial login
    db.execute("INSERT INTO logins (user_id) VALUES (?)", (new_user_id,))
    db.commit()

    session.permanent = True
    session['user_id'] = new_user_id
    session['user_name'] = name
    session['user_email'] = email
    session['role'] = 'user'

    return jsonify({'success': True, 'redirect': url_for('user_dashboard')})


@app.route('/logout')
def logout():
    """User logout."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Dedicated Admin login portal."""
    if request.method == 'GET':
        if session.get('user_id') and session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html')

    data = request.get_json(silent=True) or request.form
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    db = get_db()
    user = db.execute(
        "SELECT id, name, email, password_hash, role, status FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'success': False, 'message': 'Invalid administrative credentials'}), 401

    if user['role'] != 'admin':
        return jsonify({'success': False, 'message': 'Access denied: User is not an administrator'}), 403

    if user['status'] != 'active':
        return jsonify({'success': False, 'message': 'Administrator account has been disabled'}), 403

    # Record admin login
    db.execute("INSERT INTO logins (user_id) VALUES (?)", (user['id'],))
    db.commit()

    session.permanent = True
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['role'] = 'admin'

    return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})


@app.route('/admin/logout')
def admin_logout():
    """Admin logout."""
    session.clear()
    return redirect(url_for('admin_login'))


# ==============================================================================
# USER APPLICATION & API ENDPOINTS
# ==============================================================================

@app.route('/app')
@login_required
def user_dashboard():
    """Serves the main application page for logged-in users."""
    return render_template('app.html')


@app.route('/api/me')
@login_required
def get_current_user():
    """Returns current authenticated user details."""
    db = get_db()
    user = db.execute(
        "SELECT id, name, email, role, created_at FROM users WHERE id = ?",
        (session['user_id'],)
    ).fetchone()

    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'created_at': user['created_at']
        }
    })


@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """Allows authenticated user to update their name and/or password."""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if len(name) < 2:
        return jsonify({'success': False, 'message': 'Name must be at least 2 characters long'}), 400

    db = get_db()
    user = db.execute("SELECT id, password_hash FROM users WHERE id = ?", (session['user_id'],)).fetchone()

    if new_password:
        if not current_password or not check_password_hash(user['password_hash'], current_password):
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400

        if len(new_password) < 8 or not re.search(r'[a-zA-Z]', new_password) or not re.search(r'[0-9]', new_password):
            return jsonify({
                'success': False,
                'message': 'New password must have 8+ characters, at least 1 letter and 1 number'
            }), 400

        new_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET name = ?, password_hash = ? WHERE id = ?", (name, new_hash, session['user_id']))
    else:
        db.execute("UPDATE users SET name = ? WHERE id = ?", (name, session['user_id']))

    db.commit()
    session['user_name'] = name
    return jsonify({'success': True, 'message': 'Profile updated successfully'})


@app.route('/api/dashboard-summary')
@login_required
def dashboard_summary():
    """
    Returns high-level statistics for the user dashboard:
    - Total balance, total income, total expenses
    - 12-month bar chart breakdown for current year
    - Category-wise expense doughnut chart data
    - Current month spending breakdown
    - Recent transactions list
    """
    user_id = session['user_id']
    db = get_db()
    current_year = str(datetime.now().year)
    current_year_month = datetime.now().strftime('%Y-%m')

    # Total Income & Expenses
    totals = db.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expenses
        FROM transactions
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    # 12-month Income vs Expense breakdown for current year
    monthly_rows = db.execute("""
        SELECT
            CAST(strftime('%m', date) AS INTEGER) AS month_num,
            type,
            SUM(amount) AS total
        FROM transactions
        WHERE user_id = ? AND strftime('%Y', date) = ?
        GROUP BY month_num, type
        ORDER BY month_num ASC
    """, (user_id, current_year)).fetchall()

    monthly_map = {m: {'month': m, 'income': 0.0, 'expense': 0.0} for m in range(1, 13)}
    for r in monthly_rows:
        m = r['month_num']
        if m in monthly_map:
            if r['type'] == 'income':
                monthly_map[m]['income'] = round(float(r['total']), 2)
            else:
                monthly_map[m]['expense'] = round(float(r['total']), 2)

    monthly_bar_data = [monthly_map[m] for m in range(1, 13)]

    # Category Breakdown for all expenses
    cat_rows = db.execute("""
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE user_id = ? AND type = 'expense'
        GROUP BY category
        ORDER BY total DESC
    """, (user_id,)).fetchall()
    category_data = {r['category']: round(float(r['total']), 2) for r in cat_rows}

    # Current Month Spending Breakdown
    month_rows = db.execute("""
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE user_id = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?
        GROUP BY category
        ORDER BY total DESC
    """, (user_id, current_year_month)).fetchall()
    this_month_cats = {r['category']: round(float(r['total']), 2) for r in month_rows}
    this_month_total = sum(this_month_cats.values())

    # Recent Transactions (up to 8)
    recent_txs = db.execute("""
        SELECT id, type, category, amount, description, date, created_at
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 8
    """, (user_id,)).fetchall()

    return jsonify({
        'success': True,
        'total_income': round(float(totals['total_income']), 2),
        'total_expenses': round(float(totals['total_expenses']), 2),
        'monthly_bar_data': monthly_bar_data,
        'category_data': category_data,
        'this_month_data': {
            'total_expense': round(this_month_total, 2),
            'categories': this_month_cats
        },
        'recent_transactions': [dict(tx) for tx in recent_txs]
    })


@app.route('/api/transactions', methods=['GET', 'POST'])
@login_required
def handle_transactions():
    """
    GET: Retrieves filtered transactions for current user.
    POST: Adds a new transaction with server-side validation.
    """
    user_id = session['user_id']
    db = get_db()

    if request.method == 'GET':
        search = request.args.get('search', '').strip()
        tx_type = request.args.get('type', '').strip().lower()
        category = request.args.get('category', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()

        query = "SELECT id, user_id, type, category, amount, description, date, created_at FROM transactions WHERE user_id = ?"
        params = [user_id]

        if search:
            query += " AND description LIKE ?"
            params.append(f"%{search}%")

        if tx_type in ('income', 'expense'):
            query += " AND type = ?"
            params.append(tx_type)

        if category:
            query += " AND category = ?"
            params.append(category)

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date DESC, id DESC"
        rows = db.execute(query, params).fetchall()

        return jsonify({
            'success': True,
            'transactions': [dict(r) for r in rows]
        })

    # Handle POST (Add Transaction)
    data = request.get_json(silent=True) or {}
    tx_type = data.get('type', '').strip().lower()
    category = data.get('category', '').strip()
    amount_raw = data.get('amount')
    description = data.get('description', '').strip()
    date_str = data.get('date', '').strip()

    # Validation
    if tx_type not in ('income', 'expense'):
        return jsonify({'success': False, 'message': 'Transaction type must be income or expense'}), 400

    valid_cats = INCOME_CATEGORIES if tx_type == 'income' else EXPENSE_CATEGORIES
    if category not in valid_cats:
        return jsonify({'success': False, 'message': f'Invalid category for {tx_type}'}), 400

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Amount must be a positive number'}), 400

    if not description:
        return jsonify({'success': False, 'message': 'Description is required'}), 400

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format (must be YYYY-MM-DD)'}), 400

    cursor = db.execute("""
        INSERT INTO transactions (user_id, type, category, amount, description, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, tx_type, category, amount, description, date_str))
    db.commit()

    return jsonify({
        'success': True,
        'message': 'Transaction created successfully',
        'id': cursor.lastrowid
    }), 201


@app.route('/api/transactions/<int:tx_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_transaction(tx_id):
    """
    PUT: Updates an existing transaction (Strict user isolation enforced).
    DELETE: Deletes an existing transaction.
    """
    user_id = session['user_id']
    db = get_db()

    # Verify transaction belongs to this user
    existing = db.execute(
        "SELECT id FROM transactions WHERE id = ? AND user_id = ?",
        (tx_id, user_id)
    ).fetchone()

    if not existing:
        return jsonify({'success': False, 'message': 'Transaction not found or unauthorized'}), 404

    if request.method == 'DELETE':
        db.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id))
        db.commit()
        return jsonify({'success': True, 'message': 'Transaction deleted successfully'})

    # Handle PUT
    data = request.get_json(silent=True) or {}
    tx_type = data.get('type', '').strip().lower()
    category = data.get('category', '').strip()
    amount_raw = data.get('amount')
    description = data.get('description', '').strip()
    date_str = data.get('date', '').strip()

    if tx_type not in ('income', 'expense'):
        return jsonify({'success': False, 'message': 'Transaction type must be income or expense'}), 400

    valid_cats = INCOME_CATEGORIES if tx_type == 'income' else EXPENSE_CATEGORIES
    if category not in valid_cats:
        return jsonify({'success': False, 'message': f'Invalid category for {tx_type}'}), 400

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Amount must be a positive number'}), 400

    if not description:
        return jsonify({'success': False, 'message': 'Description is required'}), 400

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format (must be YYYY-MM-DD)'}), 400

    db.execute("""
        UPDATE transactions
        SET type = ?, category = ?, amount = ?, description = ?, date = ?
        WHERE id = ? AND user_id = ?
    """, (tx_type, category, amount, description, date_str, tx_id, user_id))
    db.commit()

    return jsonify({'success': True, 'message': 'Transaction updated successfully'})


@app.route('/api/reports/monthly')
@login_required
def monthly_report():
    """
    Returns monthly report analytics for a specified year and month:
    - Selected month's income, expenses, savings
    - 12-month comparative table for the selected year
    """
    user_id = session['user_id']
    db = get_db()

    try:
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))
        if not (1 <= month <= 12):
            raise ValueError()
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid year or month'}), 400

    year_str = str(year)
    selected_month_str = f"{year:04d}-{month:02d}"

    # Selected month stats
    month_totals = db.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expenses
        FROM transactions
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, selected_month_str)).fetchone()

    # 12-Month Table data for the requested year
    annual_rows = db.execute("""
        SELECT
            CAST(strftime('%m', date) AS INTEGER) AS m,
            type,
            SUM(amount) AS total
        FROM transactions
        WHERE user_id = ? AND strftime('%Y', date) = ?
        GROUP BY m, type
        ORDER BY m ASC
    """, (user_id, year_str)).fetchall()

    months_summary = {m: {'month': m, 'income': 0.0, 'expenses': 0.0} for m in range(1, 13)}
    for r in annual_rows:
        m = r['m']
        if m in months_summary:
            if r['type'] == 'income':
                months_summary[m]['income'] = round(float(r['total']), 2)
            else:
                months_summary[m]['expenses'] = round(float(r['total']), 2)

    return jsonify({
        'success': True,
        'year': year,
        'selected_month': month,
        'selected_month_data': {
            'income': round(float(month_totals['income']), 2),
            'expenses': round(float(month_totals['expenses']), 2)
        },
        'twelve_months_data': [months_summary[m] for m in range(1, 13)]
    })


@app.route('/api/budgets', methods=['GET', 'POST'])
@login_required
def handle_budgets():
    """
    GET: Returns category monthly budgets and calculates current month spend vs budget.
    POST: Sets or updates a category budget.
    """
    user_id = session['user_id']
    db = get_db()
    current_year_month = datetime.now().strftime('%Y-%m')

    if request.method == 'GET':
        budgets_rows = db.execute("""
            SELECT b.category, b.monthly_limit,
                   COALESCE(SUM(t.amount), 0) AS current_month_spent
            FROM budgets b
            LEFT JOIN transactions t
              ON t.user_id = b.user_id
             AND t.category = b.category
             AND t.type = 'expense'
             AND strftime('%Y-%m', t.date) = ?
            WHERE b.user_id = ?
            GROUP BY b.category, b.monthly_limit
            ORDER BY b.category ASC
        """, (current_year_month, user_id)).fetchall()

        return jsonify({
            'success': True,
            'budgets': [{
                'category': r['category'],
                'monthly_limit': round(float(r['monthly_limit']), 2),
                'current_month_spent': round(float(r['current_month_spent']), 2)
            } for r in budgets_rows]
        })

    # POST (Set Budget)
    data = request.get_json(silent=True) or {}
    category = data.get('category', '').strip()
    limit_raw = data.get('monthly_limit')

    if category not in EXPENSE_CATEGORIES:
        return jsonify({'success': False, 'message': 'Invalid expense category for budget'}), 400

    try:
        monthly_limit = float(limit_raw)
        if monthly_limit <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Monthly limit must be a positive number'}), 400

    db.execute("""
        INSERT INTO budgets (user_id, category, monthly_limit)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, category) DO UPDATE SET
            monthly_limit = excluded.monthly_limit
    """, (user_id, category, monthly_limit))
    db.commit()

    return jsonify({'success': True, 'message': f'Budget set for {category}'})


@app.route('/api/budgets/<category>', methods=['DELETE'])
@login_required
def delete_budget(category):
    """Deletes a budget limit for a category."""
    user_id = session['user_id']
    db = get_db()
    db.execute("DELETE FROM budgets WHERE user_id = ? AND category = ?", (user_id, category))
    db.commit()
    return jsonify({'success': True, 'message': f'Budget for {category} deleted'})


@app.route('/api/transactions/export')
@login_required
def export_transactions_csv():
    """
    Generates and returns a CSV file of the user's transactions.
    Guaranteed protection against CSV formula injection.
    """
    user_id = session['user_id']
    db = get_db()
    rows = db.execute("""
        SELECT id, type, category, amount, description, date, created_at
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
    """, (user_id,)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Type', 'Category', 'Description', 'Amount (INR)', 'Date', 'Created At'])

    for r in rows:
        writer.writerow([
            sanitize_csv_value(r['id']),
            sanitize_csv_value(r['type']),
            sanitize_csv_value(r['category']),
            sanitize_csv_value(r['description']),
            sanitize_csv_value(f"{r['amount']:.2f}"),
            sanitize_csv_value(r['date']),
            sanitize_csv_value(r['created_at'])
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f"attachment; filename=spendwise_export_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    return response


# ==============================================================================
# ADMIN CONSOLE & API ENDPOINTS
# ==============================================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Serves the separate administration portal."""
    return render_template('admin.html')


@app.route('/api/admin/stats')
@admin_required
def admin_stats():
    """
    Returns administrative statistics:
    - Total registered users
    - Total user logins recorded
    - Total transactions across system
    - Total money tracked
    - Login count over the last 7 active days
    - Recent user activity feed
    """
    db = get_db()

    total_users = db.execute("SELECT COUNT(*) AS c FROM users WHERE role != 'admin'").fetchone()['c']
    total_logins = db.execute("SELECT COUNT(*) AS c FROM logins").fetchone()['c']
    total_txs = db.execute("SELECT COUNT(*) AS c FROM transactions").fetchone()['c']
    total_money = db.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM transactions").fetchone()['s']

    # Logins over the last 7 active days
    login_days = db.execute("""
        SELECT date(ts) AS day, COUNT(*) AS count
        FROM logins
        GROUP BY day
        ORDER BY day DESC
        LIMIT 7
    """).fetchall()

    # Reverse to chronological order (oldest to newest)
    chart_logins = [{'date': r['day'], 'count': r['count']} for r in reversed(login_days)]

    # Recent activity feed (latest 12 logins)
    recent_activity_rows = db.execute("""
        SELECT l.id, l.ts, u.name, u.email
        FROM logins l
        JOIN users u ON l.user_id = u.id
        ORDER BY l.ts DESC
        LIMIT 12
    """).fetchall()

    recent_activity = [{
        'id': r['id'],
        'user_name': r['name'],
        'user_email': r['email'],
        'type': 'login',
        'description': 'signed in to platform',
        'timestamp': r['ts']
    } for r in recent_activity_rows]

    return jsonify({
        'success': True,
        'total_users': total_users,
        'total_logins': total_logins,
        'total_transactions': total_txs,
        'total_money_tracked': round(float(total_money), 2),
        'logins_7_days': chart_logins,
        'recent_activity': recent_activity
    })


@app.route('/api/admin/users')
@admin_required
def admin_users():
    """
    Returns registered users list for administration.
    CRITICAL SECURITY RULE: The admin must NOT be able to see or modify user passwords.
    Never select or return password_hash in this query.
    """
    db = get_db()

    users_rows = db.execute("""
        SELECT
            u.id,
            u.name,
            u.email,
            u.role,
            u.status,
            u.created_at,
            COUNT(DISTINCT l.id) AS login_count,
            MAX(l.ts) AS last_login,
            COUNT(DISTINCT t.id) AS transaction_count
        FROM users u
        LEFT JOIN logins l ON u.id = l.user_id
        LEFT JOIN transactions t ON u.id = t.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """).fetchall()

    users_list = []
    for u in users_rows:
        users_list.append({
            'id': u['id'],
            'name': u['name'],
            'email': u['email'],
            'role': u['role'],
            'status': u['status'],
            'created_at': u['created_at'],
            'login_count': u['login_count'],
            'last_login': u['last_login'],
            'transaction_count': u['transaction_count']
        })

    return jsonify({'success': True, 'users': users_list})


@app.route('/api/admin/users/<int:user_id>/status', methods=['POST'])
@admin_required
def update_user_status(user_id):
    """Enables or disables a user account. Cannot disable another administrator."""
    db = get_db()
    target_user = db.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()

    if not target_user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    if target_user['role'] == 'admin':
        return jsonify({'success': False, 'message': 'Administrator accounts cannot be disabled'}), 400

    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '').strip().lower()

    if new_status not in ('active', 'disabled'):
        return jsonify({'success': False, 'message': 'Invalid status. Must be active or disabled'}), 400

    db.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
    db.commit()

    return jsonify({'success': True, 'message': f'User account marked as {new_status}'})


# ==============================================================================
# GLOBAL ERROR HANDLERS
# ==============================================================================

@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Requested resource was not found'}), 404
    return "<h1>404 Not Found</h1><p>The requested page does not exist. <a href='/'>Return to SpendWise</a></p>", 404


@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
    return "<h1>500 Server Error</h1><p>Something went wrong on our end. <a href='/'>Return to SpendWise</a></p>", 500


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

# Initialize the database and seed admin upon startup
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"[SpendWise] Server running at http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
