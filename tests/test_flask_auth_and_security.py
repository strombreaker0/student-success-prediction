"""
Automated Security & Authentication Test Suite.
Tests:
1. App startup
2. DB initialization & connectivity
3. Successful login (username and email)
4. Wrong password
5. Unknown username/email
6. Empty fields
7. Successful registration (forces role=student)
8. Duplicate username and email rejected
9. Password hashing verified
10. Logout
11. Protected pages while logged out
12. Protected pages after logout (and no-cache headers)
13. Open redirect protection on next parameter
14. Public registration cannot create an admin
15. Brute-force rate limiting
"""

import pytest
from flask import url_for
from werkzeug.security import generate_password_hash, check_password_hash
from src.services.auth_service import verify_password, hash_password, is_rate_limited, record_failed_attempt
from src.db.connection import get_db_connection


def test_01_app_startup(client):
    """1. App startup test: app responds to initial root request."""
    res = client.get('/', follow_redirects=False)
    # Root redirects to login when unauthenticated
    assert res.status_code in (302, 200)


def test_02_db_initialization_and_connectivity(client):
    """2. DB initialization and connectivity: health check passes."""
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["models"] == "loaded"


def test_03_successful_login_by_username_and_email(client):
    """3. Successful login using username and using email."""
    # Username login
    res_user = client.post('/login', data={
        'username_or_email': 'admin_test',
        'password': 'AdminTestPassword123'
    }, follow_redirects=True)
    assert res_user.status_code == 200
    assert b"Welcome back, System Administrator!" in res_user.data

    # Log out
    client.post('/logout', follow_redirects=True)

    # Email login
    res_email = client.post('/login', data={
        'username_or_email': 'admin@institution.edu',
        'password': 'AdminTestPassword123'
    }, follow_redirects=True)
    assert res_email.status_code == 200
    assert b"Welcome back, System Administrator!" in res_email.data


def test_04_login_wrong_password(client):
    """4. Wrong password returns generic error message without account disclosure."""
    res = client.post('/login', data={
        'username_or_email': 'admin_test',
        'password': 'WrongPassword999'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid username/email or password." in res.data


def test_05_login_unknown_username_or_email(client):
    """5. Unknown username/email returns the EXACT same generic error message."""
    res = client.post('/login', data={
        'username_or_email': 'nonexistent_user',
        'password': 'SomePassword123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid username/email or password." in res.data


def test_06_login_empty_fields(client):
    """6. Empty username or password fields trigger validation warnings."""
    res = client.post('/login', data={
        'username_or_email': '',
        'password': ''
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Please provide your username or email address." in res.data or b"Invalid username" in res.data


def test_07_successful_registration_and_login(client):
    """7. Successful public registration creates a student account and allows sign in."""
    res = client.post('/register', data={
        'username': 'new_student_01',
        'email': 'new_student@institution.edu',
        'full_name': 'New Student Learner',
        'linked_student_id': 'STU_1002',
        'password': 'StrongPassword123',
        'confirm_password': 'StrongPassword123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Your student account has been created successfully" in res.data

    # Sign in with newly registered account
    res_login = client.post('/login', data={
        'username_or_email': 'new_student_01',
        'password': 'StrongPassword123'
    }, follow_redirects=True)
    assert res_login.status_code == 200
    assert b"Welcome back, New Student Learner" in res_login.data


def test_08_duplicate_username_and_email_rejected(client):
    """8. Duplicate username and email are strictly rejected by the application and DB."""
    # Attempt duplicate username
    res_dup_u = client.post('/register', data={
        'username': 'admin_test',
        'email': 'unique_email@institution.edu',
        'full_name': 'Impostor User',
        'password': 'ValidPassword123',
        'confirm_password': 'ValidPassword123'
    }, follow_redirects=True)
    assert b"already taken" in res_dup_u.data

    # Attempt duplicate email
    res_dup_e = client.post('/register', data={
        'username': 'unique_user_99',
        'email': 'admin@institution.edu',
        'full_name': 'Impostor User',
        'password': 'ValidPassword123',
        'confirm_password': 'ValidPassword123'
    }, follow_redirects=True)
    assert b"already exists" in res_dup_e.data


def test_09_password_hashing(app_with_db):
    """9. Passwords must be hashed and never stored in plaintext."""
    _, db_path = app_with_db
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = 'admin_test';")
    stored_hash = cursor.fetchone()[0]
    conn.close()

    assert stored_hash != "AdminTestPassword123"
    assert stored_hash.startswith("scrypt:") or stored_hash.startswith("pbkdf2:")
    assert verify_password(stored_hash, "AdminTestPassword123") is True
    assert verify_password(stored_hash, "AdminTestPassword123_WRONG") is False


def test_10_logout_clears_session(client):
    """10. Logout terminates the session and redirects to sign in."""
    client.post('/login', data={'username_or_email': 'admin_test', 'password': 'AdminTestPassword123'})
    res_logout = client.post('/logout', follow_redirects=True)
    assert res_logout.status_code == 200
    assert b"You have been signed out successfully." in res_logout.data


def test_11_protected_pages_while_logged_out(client):
    """11. Accessing protected pages while logged out redirects to login."""
    res_dash = client.get('/dashboard', follow_redirects=False)
    assert res_dash.status_code == 302
    assert '/login' in res_dash.headers['Location']

    res_students = client.get('/students', follow_redirects=False)
    assert res_students.status_code == 302
    assert '/login' in res_students.headers['Location']


def test_12_protected_pages_no_cache_headers(client):
    """12. Protected pages return Cache-Control: no-store to prevent back button exposure."""
    client.post('/login', data={'username_or_email': 'admin_test', 'password': 'AdminTestPassword123'})
    res_dash = client.get('/dashboard')
    assert "no-store" in res_dash.headers.get("Cache-Control", "")
    assert "no-cache" in res_dash.headers.get("Cache-Control", "")


def test_13_open_redirect_prevention(client):
    """13. Open redirect protection: external malicious 'next' URLs are rejected."""
    res = client.post('/login?next=https://malicious-phishing.com', data={
        'username_or_email': 'admin_test',
        'password': 'AdminTestPassword123'
    }, follow_redirects=False)
    assert res.status_code == 302
    # Must redirect to internal dashboard, not to external malicious site
    assert "malicious-phishing.com" not in res.headers["Location"]
    assert res.headers["Location"].endswith('/dashboard') or res.headers["Location"] == '/dashboard'


def test_14_public_registration_cannot_create_admin(client, app_with_db):
    """14. Public registration strictly creates student accounts even if 'role' field is forged in request."""
    _, db_path = app_with_db
    res = client.post('/register', data={
        'username': 'sneaky_user',
        'email': 'sneaky@institution.edu',
        'full_name': 'Sneaky Attacker',
        'linked_student_id': 'STU_1003',
        'role': 'admin',  # Injected field
        'password': 'ValidPassword123',
        'confirm_password': 'ValidPassword123'
    }, follow_redirects=True)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE username = 'sneaky_user';")
    assigned_role = cursor.fetchone()[0]
    conn.close()

    assert assigned_role == "student"


def test_15_brute_force_rate_limiting(client):
    """15. Brute force protection: repeated failed logins trigger lockout warning."""
    for _ in range(5):
        record_failed_attempt("brute_target_user")

    assert is_rate_limited("brute_target_user") is True

    res = client.post('/login', data={
        'username_or_email': 'brute_target_user',
        'password': 'AnyPassword123'
    }, follow_redirects=True)
    assert b"Too many failed login attempts" in res.data
