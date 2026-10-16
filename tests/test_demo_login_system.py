"""
Automated Test Suite for Demo Login System.
Tests:
1. Admin demo login succeeds and grants admin access.
2. Student demo login succeeds and lands on personal student portal.
3. Invalid credentials and roles are rejected.
4. Admin-only pages reject the student demo account (403 Forbidden).
5. Student demo account cannot access other students' records or reports (IDOR defense).
6. Logout clears the demo session completely.
7. Re-running demo provisioning is idempotent (no duplicates, no disruption of existing records).
8. Unprovisioned demo login displays helpful guidance without crashing.
9. CSRF protection is enforced on demo-login endpoint.
"""

import os
import pytest
from src.services.demo_service import (
    provision_demo_accounts,
    DEMO_ADMIN_USERNAME,
    DEMO_STUDENT_USERNAME,
    DEMO_STUDENT_ID
)
from src.db.connection import get_db_connection


@pytest.fixture
def provisioned_demo(app_with_db):
    """Ensures demo accounts and synthetic student profile exist in the isolated test DB."""
    app, db_path = app_with_db
    conn = get_db_connection(db_path)
    try:
        provision_demo_accounts(conn=conn)
    finally:
        conn.close()
    return app, db_path


def test_01_admin_demo_login_succeeds(client, provisioned_demo):
    """1. Admin demo login succeeds through backend and accesses executive dashboard."""
    res = client.post('/demo-login', data={'demo_role': 'admin'}, follow_redirects=True)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    # Check that user is signed in as admin
    assert "Signed in as Demo Admin" in html or "Institutional Demo Administrator" in html
    # Check executive dashboard content
    assert "Executive Overview" in html or "Dashboard" in html


def test_02_student_demo_login_succeeds(client, provisioned_demo):
    """2. Student demo login succeeds through backend and lands on linked student profile."""
    res = client.post('/demo-login', data={'demo_role': 'student'}, follow_redirects=True)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    # Check that user lands on their student profile
    assert "Signed in as Demo Student" in html or DEMO_STUDENT_ID in html
    assert DEMO_STUDENT_ID in html


def test_03_invalid_demo_role_and_credentials_rejected(client, provisioned_demo):
    """3. Invalid demo roles and tampered credentials are safely rejected."""
    # Invalid role
    res_bad_role = client.post('/demo-login', data={'demo_role': 'super_hacker'}, follow_redirects=True)
    assert res_bad_role.status_code == 200
    assert "Invalid demo login request" in res_bad_role.get_data(as_text=True)

    # Empty role
    res_empty = client.post('/demo-login', data={'demo_role': ''}, follow_redirects=True)
    assert res_empty.status_code == 200
    assert "Invalid demo login request" in res_empty.get_data(as_text=True)

    # Manual login with wrong password for demo_admin
    res_bad_pwd = client.post('/login', data={
        'username_or_email': DEMO_ADMIN_USERNAME,
        'password': 'WrongPassword123!'
    }, follow_redirects=True)
    assert res_bad_pwd.status_code == 200
    assert "Invalid username/email or password" in res_bad_pwd.get_data(as_text=True)


def test_04_admin_only_pages_reject_student_demo(client, provisioned_demo):
    """4. Admin-only pages reject the student demo account with HTTP 403."""
    # Sign in as student demo
    client.post('/demo-login', data={'demo_role': 'student'}, follow_redirects=True)

    # Forbidden: create student
    res_new = client.get('/students/new')
    assert res_new.status_code == 403

    # Forbidden: bulk CSV upload
    res_bulk = client.get('/students/bulk-upload')
    assert res_bulk.status_code == 403

    # Forbidden: CSV export
    res_export = client.get('/students/export')
    assert res_export.status_code == 403

    # Forbidden: system audit trail
    res_audit = client.get('/audit')
    assert res_audit.status_code == 403

    # Forbidden: model transparency specifications
    res_transp = client.get('/transparency')
    assert res_transp.status_code == 403


def test_05_students_cannot_access_other_students_records(client, provisioned_demo):
    """5. Student demo account cannot access other students' records or dossier reports (IDOR)."""
    # Sign in as student demo
    client.post('/demo-login', data={'demo_role': 'student'}, follow_redirects=True)

    # Allowed: Access own synthetic student profile
    res_own = client.get(f'/students/{DEMO_STUDENT_ID}')
    assert res_own.status_code == 200

    # Forbidden: Access existing other student profiles
    res_other1 = client.get('/students/STU_1001')
    assert res_other1.status_code == 403

    res_other2 = client.get('/students/STU_1002')
    assert res_other2.status_code == 403

    # Forbidden: Generate PDF dossier for another student
    res_pdf_forbidden = client.get('/students/STU_1001/report/pdf')
    assert res_pdf_forbidden.status_code == 403

    # Allowed: Generate PDF dossier for own student ID
    res_pdf_own = client.get(f'/students/{DEMO_STUDENT_ID}/report/pdf')
    assert res_pdf_own.status_code == 200
    assert res_pdf_own.mimetype == "application/pdf"


def test_06_logout_clears_session(client, provisioned_demo):
    """6. Logout clears the demo session and blocks subsequent protected page access."""
    # Sign in as admin demo
    client.post('/demo-login', data={'demo_role': 'admin'}, follow_redirects=True)

    # Verify access to dashboard
    res_dash = client.get('/dashboard')
    assert res_dash.status_code == 200

    # Log out
    res_logout = client.post('/logout', follow_redirects=True)
    assert res_logout.status_code == 200
    assert "You have been signed out successfully" in res_logout.get_data(as_text=True)

    # Attempting to access dashboard after logout redirects to login
    res_dash_after = client.get('/dashboard', follow_redirects=False)
    assert res_dash_after.status_code == 302
    assert "/login" in res_dash_after.headers["Location"]


def test_07_rerunning_provisioning_is_idempotent(app_with_db):
    """7. Re-running demo provisioning is strictly idempotent and does not corrupt existing users."""
    app, db_path = app_with_db
    conn = get_db_connection(db_path)
    try:
        # First execution
        res1 = provision_demo_accounts(conn=conn)
        assert res1["admin"]["action"] in ("created", "updated")
        assert res1["student"]["action"] in ("created", "updated")

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?;", (DEMO_ADMIN_USERNAME,))
        assert cursor.fetchone()[0] == 1

        # Second execution
        res2 = provision_demo_accounts(conn=conn)
        assert res2["admin"]["action"] == "updated"
        assert res2["student"]["action"] == "updated"

        # Check total demo users remain exactly 2
        cursor.execute("SELECT COUNT(*) FROM users WHERE username IN (?, ?);", (DEMO_ADMIN_USERNAME, DEMO_STUDENT_USERNAME))
        assert cursor.fetchone()[0] == 2

        # Verify existing fixture accounts were not altered
        cursor.execute("SELECT role FROM users WHERE username = 'admin_test';")
        row = cursor.fetchone()
        assert row is not None and row["role"] == "admin"
    finally:
        conn.close()


def test_08_unprovisioned_demo_account_returns_helpful_message(client, app_with_db):
    """8. Demo login on an unprovisioned system shows clear setup instructions without crashing."""
    # Do NOT call provision_demo_accounts
    res = client.post('/demo-login', data={'demo_role': 'admin'}, follow_redirects=True)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "has not been provisioned yet" in html


def test_09_csrf_protection_enforced_on_demo_login(csrf_client, provisioned_demo):
    """9. When CSRF is enabled, demo-login POST requests without token are rejected with 400 Bad Request."""
    res = csrf_client.post('/demo-login', data={'demo_role': 'admin'}, follow_redirects=True)
    assert res.status_code == 400


def test_10_demo_admin_cannot_view_modify_or_delete_real_students(client, provisioned_demo):
    """10. Demo admin cannot view, edit, or delete real production student records."""
    # Sign in as demo admin
    res = client.post('/demo-login', data={'demo_role': 'admin'}, follow_redirects=True)
    assert res.status_code == 200

    # View real student record -> 403 Forbidden
    res_view = client.get('/students/STU_1001')
    assert res_view.status_code == 403

    # Edit form for real student record -> 403 Forbidden
    res_edit_get = client.get('/students/STU_1001/edit')
    assert res_edit_get.status_code == 403

    # Submit edit to real student record -> 403 Forbidden
    res_edit_post = client.post('/students/STU_1001/edit', data={
        'student_id': 'STU_1001',
        'attendance_rate': 99.0,
        'study_hours_per_week': 20.0,
        'previous_scores': 85.0,
        'assignment_completion_rate': 95.0,
        'tutoring_sessions': 1,
        'sleep_hours': 8.0,
        'extracurricular': '1',
        'internet_access': '1'
    })
    assert res_edit_post.status_code == 403

    # Delete real student record -> 403 Forbidden
    res_delete = client.post('/students/STU_1001/delete')
    assert res_delete.status_code == 403


def test_11_demo_admin_can_manage_synthetic_demo_records(client, provisioned_demo):
    """11. Demo admin can view and manage synthetic demo records (STU_DEMO*)."""
    # Sign in as demo admin
    client.post('/demo-login', data={'demo_role': 'admin'}, follow_redirects=True)

    # Can view synthetic demo student profile
    res_view = client.get('/students/STU_DEMO01')
    assert res_view.status_code == 200
    assert "STU_DEMO01" in res_view.get_data(as_text=True)

    # Can load edit form for synthetic demo student
    res_edit_get = client.get('/students/STU_DEMO02/edit')
    assert res_edit_get.status_code == 200

    # Can delete synthetic demo student
    res_delete = client.post('/students/STU_DEMO05/delete', follow_redirects=True)
    assert res_delete.status_code == 200
    html_delete = res_delete.get_data(as_text=True)
    assert "was deleted" in html_delete
    assert "STU_DEMO05" in html_delete


def test_12_enable_demo_login_disabled(client, provisioned_demo):
    """12. Disabling ENABLE_DEMO_LOGIN hides UI buttons and blocks demo login endpoint."""
    app, _ = provisioned_demo
    app.config["ENABLE_DEMO_LOGIN"] = False

    try:
        # Check login page does not display demo buttons
        res_page = client.get('/login')
        assert res_page.status_code == 200
        html = res_page.get_data(as_text=True)
        assert "Continue as Admin Demo" not in html
        assert "Continue as Student Demo" not in html

        # Direct POST to demo-login is rejected
        res_post = client.post('/demo-login', data={'demo_role': 'admin'}, follow_redirects=True)
        assert res_post.status_code == 200
        assert "Demo login is currently disabled" in res_post.get_data(as_text=True)
    finally:
        app.config["ENABLE_DEMO_LOGIN"] = True


def test_13_demo_admin_dashboard_and_search_scoping(client, provisioned_demo):
    """13. Demo admin dashboard and global search are scoped strictly to synthetic demo records."""
    client.post('/demo-login', data={'demo_role': 'admin'}, follow_redirects=True)

    # Dashboard loads cleanly
    res_dash = client.get('/dashboard')
    assert res_dash.status_code == 200
    dash_html = res_dash.get_data(as_text=True)
    # Real students must not appear in "needs attention" or recent predictions
    assert "STU_1001" not in dash_html
    assert "STU_1002" not in dash_html

    # Search for real student returns empty list
    res_search_real = client.get('/search?q=STU_1001')
    assert res_search_real.status_code == 200
    assert res_search_real.get_json() == []

    # Search for demo student returns matching synthetic record
    res_search_demo = client.get('/search?q=DEMO')
    assert res_search_demo.status_code == 200
    demo_results = res_search_demo.get_json()
    assert len(demo_results) > 0
    assert any("STU_DEMO" in item["label"] for item in demo_results)
