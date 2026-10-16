"""
Test Suite for Public Admin Demo Dashboard & Synthetic Isolation.
Verifies:
1. Homepage route (/) directly opens the dedicated Admin Demo Dashboard without requiring login (200 OK).
2. Dedicated demo routes (/demo, /demo/dashboard) open the demo dashboard directly (200 OK).
3. Demo dashboard strictly displays synthetic demo data (STU_DEMO*) and never real student records (STU_1001, etc.).
4. Real admin routes (/dashboard, /students, /students/new, /audit) strictly reject unauthenticated visitors (302 Redirect).
5. Real admin accounts still authenticate through Flask-Login and access the live dashboard with full permissions.
6. Chart data API (/api/chart-data) is isolated to synthetic records for public demo visitors.
7. Global search API (/search) allows demo queries but never leaks real student records to public visitors.
"""

import pytest
from src.services.demo_service import provision_demo_accounts, DEMO_ADMIN_USERNAME, DEMO_STUDENT_ID
from src.db.connection import get_db_connection


@pytest.fixture
def populated_test_db(app_with_db):
    """Ensures both test cohort (STU_1001-STU_1003) and synthetic demo cohort (STU_DEMO*) exist."""
    app, db_path = app_with_db
    conn = get_db_connection(db_path)
    try:
        provision_demo_accounts(conn=conn)
    finally:
        conn.close()
    return app, db_path


def test_01_homepage_opens_demo_dashboard_directly(client, populated_test_db):
    """1. Homepage (/) opens the dedicated Admin Demo Dashboard directly without redirecting to login."""
    res = client.get('/', follow_redirects=False)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Executive Analytics Dashboard (Demo)" in html or "Interactive Presentation Mode" in html
    assert "Safe Synthetic Cohort" in html or "Synthetic" in html
    assert "Admin Sign In" in html


def test_02_separate_demo_routes_open_demo_dashboard(client, populated_test_db):
    """2. Dedicated /demo and /demo/dashboard routes open the dedicated Admin Demo Dashboard."""
    res_demo = client.get('/demo', follow_redirects=False)
    assert res_demo.status_code == 200
    html_demo = res_demo.get_data(as_text=True)
    assert "Executive Analytics Dashboard (Demo)" in html_demo or "Interactive Presentation Mode" in html

    res_dash = client.get('/demo/dashboard', follow_redirects=False)
    assert res_dash.status_code == 200
    html_dash = res_dash.get_data(as_text=True)
    assert "Executive Analytics Dashboard (Demo)" in html_dash or "Interactive Presentation Mode" in html


def test_03_demo_dashboard_only_contains_synthetic_data(client, populated_test_db):
    """3. Demo dashboard displays only synthetic demo students (STU_DEMO*) and never real student records."""
    res = client.get('/')
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Synthetic demo cohort should be referenced
    assert "STU_DEMO" in html

    # Real fixture student records must NOT be exposed anywhere in the HTML
    assert "STU_1001" not in html
    assert "STU_1002" not in html
    assert "STU_1003" not in html

    # Real admin fixture usernames must NOT be leaked
    assert "admin_test" not in html
    assert "faculty_test" not in html
    assert "AdminTestPassword123" not in html


def test_04_real_admin_routes_reject_unauthenticated_visitors(client, populated_test_db):
    """4. All real admin routes, student management, and audit logs require authentication."""
    protected_routes = [
        '/dashboard',
        '/students',
        '/students/new',
        '/students/STU_1001',
        '/students/STU_1001/edit',
        '/students/bulk-upload',
        '/students/export',
        '/audit',
        '/predictions/batch'
    ]

    for route in protected_routes:
        res = client.get(route, follow_redirects=False)
        assert res.status_code == 302, f"Route {route} was not protected (expected 302, got {res.status_code})"
        assert "/login" in res.headers["Location"], f"Route {route} did not redirect to /login"


def test_05_real_admin_login_and_full_access_preserved(client, populated_test_db):
    """5. Real administrator accounts log in normally and access live production records."""
    # Authenticate as real admin fixture
    res_login = client.post('/login', data={
        'username_or_email': 'admin_test',
        'password': 'AdminTestPassword123'
    }, follow_redirects=True)
    assert res_login.status_code == 200

    # Live dashboard is accessible
    res_dash = client.get('/dashboard')
    assert res_dash.status_code == 200
    html_dash = res_dash.get_data(as_text=True)
    assert "Executive Analytics Dashboard" in html_dash

    # Real student directory is accessible
    res_students = client.get('/students')
    assert res_students.status_code == 200
    html_students = res_students.get_data(as_text=True)
    assert "STU_1001" in html_students
    assert "STU_1002" in html_students

    # Real student detail profile is accessible
    res_detail = client.get('/students/STU_1001')
    assert res_detail.status_code == 200
    assert "STU_1001" in res_detail.get_data(as_text=True)


def test_06_chart_data_api_isolated_for_public_visitors(client, populated_test_db):
    """6. Chart data API returns exclusively synthetic demo counts for unauthenticated visitors."""
    res = client.get('/api/chart-data')
    assert res.status_code == 200
    data = res.get_json()

    assert "outcomes" in data
    assert "attendance_bins" in data
    # The total outcomes in demo mode must match the synthetic cohort size (5 students), NOT the whole DB
    total_demo_outcomes = data["outcomes"]["Passed"] + data["outcomes"]["Failed"]
    assert total_demo_outcomes == 5


def test_07_global_search_isolated_for_public_visitors(client, populated_test_db):
    """7. Search endpoint is accessible to visitors but strictly returns synthetic demo results."""
    # Real student search must return empty
    res_real = client.get('/search?q=STU_1001')
    assert res_real.status_code == 200
    assert res_real.get_json() == []

    # Demo student search returns matching synthetic demo students
    res_demo = client.get('/search?q=DEMO')
    assert res_demo.status_code == 200
    results = res_demo.get_json()
    assert len(results) > 0
    assert all("STU_DEMO" in item["label"] for item in results)
