# SpendWise - Smart Expense Tracker

SpendWise is a modern, production-quality financial dashboard and expense management web application built with **Python Flask**, **SQLite3**, **Chart.js**, and vanilla **HTML5/CSS3/JavaScript**.

---

## 🌟 Key Features

### 1. User Dashboard (`/app`)
- **Metric Stat Cards**: Real-time Total Balance, Total Income, Total Expenses, and Net Savings Rate.
- **Interactive Visualizations (Chart.js)**:
  - **Expense Category Doughnut Chart**: Interactive distribution of spend across categories with hover tooltips and legends.
  - **12-Month Cashflow Bar Chart**: Annual income vs. expense comparison for the current year.
- **This Month's Spending Summary**: Dynamic category progress bars displaying percent and amount spent.
- **Recent Transactions**: Quick snapshot of latest transactions with type indicators and category badges.

### 2. Expense & Income Management
- **Add, Edit, and Delete**: Full CRUD capabilities handled seamlessly via modal forms.
- **Curated Financial Categories**:
  - **Expense**: Food, Shopping, Travel, Education, Bills, Health, Other
  - **Income**: Salary, Freelance, Business, Gift, Other
- **Robust Validation**: Server-side and client-side validation ensuring positive amounts, valid dates (`YYYY-MM-DD`), non-empty descriptions, and category verification.
- **Search & Filtering**:
  - Live debounced search across descriptions.
  - Filter by transaction type (Income / Expense).
  - Filter by category.
  - Filter by date range (Start Date & End Date).
- **Secure CSV Export**: Exports filtered transactions to CSV with **Formula Injection Protection** (automatically prefixes unsafe trigger characters `=`, `+`, `-`, `@`, `\t`, `\r` with `'`).

### 3. Monthly Financial Reports
- **Dynamic Year & Month Pickers**: Strictly lists January to December without invalid options.
- **Selected Month Overview**: Total Income, Total Expenses, Net Savings, and Savings Rate % for chosen period.
- **12-Month Performance Table**: Comprehensive breakdown of every month in the selected year, with the selected month highlighted.

### 4. Category Budgets & Overspending Alerts (Extra Feature)
- Set monthly spending limits per expense category.
- Visual progress bar tracking spending vs. budget.
- Automatic alert badges: **Safe / On Track**, **Caution (80%+)**, and **Over Budget (100%+)**.

### 5. Administrative Dashboard (`/admin`)
- **Dedicated Admin UI**: Completely separate administrative console.
- **Platform Analytics**: Total registered users, total logins, total transactions, and total money tracked.
- **7-Day Login Velocity**: Interactive line chart showing authentication frequency across the last 7 active days.
- **Recent User Activity Feed**: Live event logs of user logins and sessions.
- **User Accounts Management**: Directory of registered users with login counts, last login timestamp, transaction counts, and one-click account Enable/Disable toggles.
- **Strict Credential Protection**: Admin views never select, query, or display `password_hash`.

### 6. Security & Architecture
- **Password Hashing**: Industry-standard Werkzeug `generate_password_hash` & `check_password_hash` (scrypt / pbkdf2).
- **Session Security**: Session cookies configured with `HttpOnly` and `SameSite='Lax'`.
- **User Isolation**: Every database transaction and report query is strictly scoped to `session['user_id']`.
- **SQL Injection Prevention**: 100% parameterized queries using SQLite's `?` placeholder syntax.
- **XSS Protection**: All user-generated content is sanitized and escaped before rendering in the DOM.
- **Currency Standard**: Formatted with the Indian Rupee symbol (`₹`) centralized in formatting functions for easy customization.

---

## 📁 Project Structure

```
expense_tracker/
├── app.py                      # Flask backend, API endpoints, SQLite queries, role decorators
├── requirements.txt            # Python dependencies (Flask, Werkzeug)
├── README.md                   # Documentation and run instructions
├── test_app.py                 # Automated unit and integration test suite
├── verify_live_server.py       # Live HTTP endpoint test script
├── seed_demo_data.py           # Demo dataset populator
├── expense_tracker.db          # SQLite database (auto-created on first run)
├── templates/
│   ├── login.html              # User login page
│   ├── register.html           # User registration page with live password strength meter
│   ├── admin_login.html        # Secure administrator login portal
│   ├── app.html                # User dashboard (Dashboard, Transactions, Reports, Budgets)
│   └── admin.html              # Separate Administration Console
└── static/
    ├── css/
    │   └── style.css           # Modern design system (Plus Jakarta Sans, responsive grid, light theme)
    └── js/
        ├── app.js              # User frontend state, Chart.js integrations, modal controls, CSV export
        └── admin.js            # Admin analytics, login chart, user management
```

---

## 🚀 Step-by-Step Local Run Instructions

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- Web browser (Chrome, Edge, Firefox, Safari)

### 2. Set Up Virtual Environment (Recommended)

#### On Windows (PowerShell / Command Prompt):
```powershell
# Navigate into the project folder
cd "c:\Users\MY PC\OneDrive\Desktop\expense tracker"

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\Activate.ps1
# Or in CMD: venv\Scripts\activate.bat
```

#### On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Seed Demo Data
To immediately explore the dashboard with pre-populated multi-month transactions and category budgets:
```bash
python seed_demo_data.py
```

### 5. Run the Application
```bash
python app.py
```

The application will start on `http://127.0.0.1:5050` (or `http://localhost:5050`).

---

## 🔑 Default Credentials

| Portal | URL | Email | Password |
| :--- | :--- | :--- | :--- |
| **Demo User** | `http://127.0.0.1:5050/login` | `demo@spendwise.com` | `Password@123` |
| **Admin Portal** | `http://127.0.0.1:5050/admin/login` | `admin@expense.com` | `Admin@123` |

> *Note: Both login screens include a convenient one-click "Autofill" button for swift testing and evaluation.*

---

## ⚙️ Environment Variables (Optional)

You can customize runtime configuration via environment variables:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PORT` | `5050` | Port for the Flask server |
| `SECRET_KEY` | *(Built-in secure fallback)* | Flask secret key for signing session cookies |
| `ADMIN_EMAIL` | `admin@expense.com` | Default admin email seeded on initialization |
| `ADMIN_PASSWORD` | `Admin@123` | Default admin password seeded on initialization |

Example:
```powershell
$env:PORT="5050"
$env:ADMIN_EMAIL="myadmin@company.com"
$env:ADMIN_PASSWORD="CustomPassword@999"
python app.py
```

---

## 🧪 Running the Automated Tests

### 1. Unit & Security Test Suite
Runs isolated unit tests validating password strength requirements, invalid input rejections, transaction CRUD, user isolation, and admin password protection:
```bash
python test_app.py
```

### 2. Live HTTP Verification Script
Sends real requests against the running Flask server to verify session cookie persistence, CSV exports, Chart.js APIs, and Admin actions:
```bash
python verify_live_server.py
```
