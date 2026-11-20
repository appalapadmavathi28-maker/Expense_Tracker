"""
Live End-to-End Server Verification Script
Tests real HTTP requests and session handling against http://127.0.0.1:5000
"""

import urllib.request
import urllib.parse
import http.cookiejar
import json
import sys

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'http://127.0.0.1:5050'

def run_verification():
    print("=== STARTING LIVE HTTP VERIFICATION ===")

    # 1. Test unauthenticated root redirect
    req = urllib.request.Request(BASE_URL)
    with urllib.request.urlopen(req) as resp:
        print(f"[PASS] Root redirected to: {resp.geturl()}")
        assert '/login' in resp.geturl()

    # Create CookieJar for session tracking
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # 2. Test Login Page GET
    resp = opener.open(f'{BASE_URL}/login')
    html = resp.read().decode('utf-8')
    assert 'SpendWise' in html
    assert 'Sign In' in html
    print("[PASS] User Login page renders correctly.")

    # 3. Test Login POST with demo credentials
    login_data = json.dumps({'email': 'demo@spendwise.com', 'password': 'Password@123'}).encode('utf-8')
    login_req = urllib.request.Request(
        f'{BASE_URL}/login',
        data=login_data,
        headers={'Content-Type': 'application/json'}
    )
    resp = opener.open(login_req)
    data = json.loads(resp.read().decode('utf-8'))
    assert data['success'] is True
    print(f"[PASS] User authentication successful. Redirect: {data.get('redirect')}")

    # 4. Test /app page GET with session
    resp = opener.open(f'{BASE_URL}/app')
    app_html = resp.read().decode('utf-8')
    assert 'Dashboard' in app_html
    assert 'Monthly Reports' in app_html
    assert 'Budgets & Goals' in app_html
    print("[PASS] User Dashboard /app rendered successfully.")

    # 5. Test /api/me
    resp = opener.open(f'{BASE_URL}/api/me')
    me_data = json.loads(resp.read().decode('utf-8'))
    assert me_data['success'] is True
    assert me_data['user']['email'] == 'demo@spendwise.com'
    print(f"[PASS] /api/me returned user: {me_data['user']['name']} ({me_data['user']['email']})")

    # 6. Test /api/dashboard-summary
    resp = opener.open(f'{BASE_URL}/api/dashboard-summary')
    summary = json.loads(resp.read().decode('utf-8'))
    assert summary['success'] is True
    print(f"[PASS] Dashboard Summary: Income=₹{summary['total_income']}, Expenses=₹{summary['total_expenses']}, Recent Tx Count={len(summary['recent_transactions'])}")

    # 7. Test Add Transaction
    new_tx_data = json.dumps({
        'type': 'expense',
        'category': 'Food',
        'amount': 380.00,
        'description': 'Live Test Coffee and Croissant',
        'date': '2026-11-20'
    }).encode('utf-8')
    tx_req = urllib.request.Request(
        f'{BASE_URL}/api/transactions',
        data=new_tx_data,
        headers={'Content-Type': 'application/json'}
    )
    resp = opener.open(tx_req)
    tx_res = json.loads(resp.read().decode('utf-8'))
    assert tx_res['success'] is True
    created_id = tx_res['id']
    print(f"[PASS] Created transaction id: {created_id}")

    # 8. Test Edit Transaction
    edit_data = json.dumps({
        'type': 'expense',
        'category': 'Food',
        'amount': 420.00,
        'description': 'Live Test Coffee and Croissant (Deluxe)',
        'date': '2026-11-20'
    }).encode('utf-8')
    edit_req = urllib.request.Request(
        f'{BASE_URL}/api/transactions/{created_id}',
        data=edit_data,
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    resp = opener.open(edit_req)
    edit_res = json.loads(resp.read().decode('utf-8'))
    assert edit_res['success'] is True
    print(f"[PASS] Updated transaction id: {created_id}")

    # 9. Test Delete Transaction
    del_req = urllib.request.Request(
        f'{BASE_URL}/api/transactions/{created_id}',
        headers={'Content-Type': 'application/json'},
        method='DELETE'
    )
    resp = opener.open(del_req)
    del_res = json.loads(resp.read().decode('utf-8'))
    assert del_res['success'] is True
    print(f"[PASS] Deleted transaction id: {created_id}")

    # 10. Test Filtering & Search
    resp = opener.open(f'{BASE_URL}/api/transactions?search=Bistro')
    search_data = json.loads(resp.read().decode('utf-8'))
    assert search_data['success'] is True
    print(f"[PASS] Filter by search returned {len(search_data['transactions'])} transactions")

    # 11. Test Monthly Reports
    resp = opener.open(f'{BASE_URL}/api/reports/monthly?year=2026&month=11')
    report = json.loads(resp.read().decode('utf-8'))
    assert report['success'] is True
    assert len(report['twelve_months_data']) == 12
    print(f"[PASS] Monthly Reports: 12-month annual table verified, Month 11 Income=₹{report['selected_month_data']['income']}, Expense=₹{report['selected_month_data']['expenses']}")

    # 12. Test Budgets
    resp = opener.open(f'{BASE_URL}/api/budgets')
    budgets_data = json.loads(resp.read().decode('utf-8'))
    assert budgets_data['success'] is True
    print(f"[PASS] Budgets endpoint verified with {len(budgets_data['budgets'])} category budgets")

    # 13. Test CSV Export
    resp = opener.open(f'{BASE_URL}/api/transactions/export')
    assert 'text/csv' in resp.headers.get('Content-Type', '')
    csv_body = resp.read().decode('utf-8')
    assert 'Amount (INR)' in csv_body
    print(f"[PASS] CSV Export returned valid CSV data ({len(csv_body.splitlines())} lines)")

    # 14. Test Admin Flow
    admin_cj = http.cookiejar.CookieJar()
    admin_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(admin_cj))

    admin_login_data = json.dumps({'email': 'admin@expense.com', 'password': 'Admin@123'}).encode('utf-8')
    admin_req = urllib.request.Request(
        f'{BASE_URL}/admin/login',
        data=admin_login_data,
        headers={'Content-Type': 'application/json'}
    )
    resp = admin_opener.open(admin_req)
    admin_res = json.loads(resp.read().decode('utf-8'))
    assert admin_res['success'] is True
    print(f"[PASS] Admin login successful.")

    # Admin Portal page GET
    resp = admin_opener.open(f'{BASE_URL}/admin')
    admin_html = resp.read().decode('utf-8')
    assert 'System Management' in admin_html
    print("[PASS] Admin Portal /admin rendered successfully.")

    # Admin Stats API
    resp = admin_opener.open(f'{BASE_URL}/api/admin/stats')
    stats = json.loads(resp.read().decode('utf-8'))
    assert stats['success'] is True
    assert stats['total_users'] >= 1
    assert stats['total_transactions'] >= 1
    assert 'logins_7_days' in stats
    print(f"[PASS] Admin Stats verified: {stats['total_users']} users, {stats['total_transactions']} transactions, ₹{stats['total_money_tracked']} tracked.")

    # Admin Users API (Verify password_hash is omitted)
    resp = admin_opener.open(f'{BASE_URL}/api/admin/users')
    users_data = json.loads(resp.read().decode('utf-8'))
    assert users_data['success'] is True
    for u in users_data['users']:
        assert 'password_hash' not in u
        assert 'name' in u
        assert 'email' in u
    print(f"[PASS] Admin Users directory verified: {len(users_data['users'])} users listed, password_hash strictly omitted.")

    print("\n>>> ALL LIVE VERIFICATION CHECKS COMPLETED SUCCESSFULLY! <<<")

if __name__ == '__main__':
    run_verification()
