"""
Role-Based Access Control (RBAC) and IDOR Isolation Test Suite.
Tests:
- Admin role capabilities
- Faculty role capabilities and boundaries
- Student self-service isolation (IDOR protection)
- Unauthorized role access restrictions
"""

import pytest


def login_as(client, username, password):
    client.post('/logout', follow_redirects=True)
    return client.post('/login', data={'username_or_email': username, 'password': password}, follow_redirects=True)


def test_admin_full_access(client):
    """Admin has full clearance across all management and audit interfaces."""
    login_as(client, 'admin_test', 'AdminTestPassword123')

    # Can access dashboard
    assert client.get('/dashboard').status_code == 200
    # Can access student directory
    assert client.get('/students').status_code == 200
    # Can access new student form
    assert client.get('/students/new').status_code == 200
    # Can access audit logs
    assert client.get('/audit').status_code == 200
    # Can access batch screening
    assert client.get('/predictions/batch').status_code == 200
    # Can access model transparency
    assert client.get('/transparency').status_code == 200


def test_faculty_permissions_and_boundaries(client):
    """Faculty can manage students, run predictions, but cannot delete or view audit logs."""
    login_as(client, 'faculty_test', 'TeacherTestPassword123')

    # Can access dashboard and student management
    assert client.get('/dashboard').status_code == 200
    assert client.get('/students').status_code == 200
    assert client.get('/students/new').status_code == 200
    assert client.get('/predictions/batch').status_code == 200
    assert client.get('/transparency').status_code == 200

    # BLOCKED from audit logs (403 Forbidden)
    assert client.get('/audit').status_code == 403

    # BLOCKED from deleting students (403 Forbidden)
    res_del = client.post('/students/STU_1002/delete')
    assert res_del.status_code == 403


def test_student_isolation_and_idor_prevention(client):
    """
    Student user:
    - CAN access their own profile (STU_1001)
    - CANNOT access another student's profile (STU_1002) -> 403 Forbidden (IDOR prevented)
    - CANNOT access student directory -> redirected / blocked
    - CANNOT access batch screening -> 403 Forbidden
    - CANNOT access audit logs -> 403 Forbidden
    - CANNOT create or delete students -> 403 Forbidden
    """
    login_as(client, 'student_test', 'StudentTestPassword123')

    # Can access their own profile
    res_own = client.get('/students/STU_1001')
    assert res_own.status_code == 200
    assert b"STU_1001" in res_own.data

    # IDOR Test: Try to view STU_1002
    res_other = client.get('/students/STU_1002')
    assert res_other.status_code == 403

    # Blocked from student management directory
    res_dir = client.get('/students', follow_redirects=False)
    # Redirects directly to their own profile
    assert res_dir.status_code == 302
    assert "STU_1001" in res_dir.headers["Location"]

    # Blocked from batch screening
    assert client.get('/predictions/batch').status_code == 403

    # Blocked from audit logs
    assert client.get('/audit').status_code == 403

    # Blocked from adding students
    assert client.get('/students/new').status_code == 403
    assert client.post('/students/new', data={}).status_code == 403


def test_student_pdf_idor_prevention(client):
    """Student can download their own assessment PDF, but is blocked from downloading another's PDF."""
    login_as(client, 'student_test', 'StudentTestPassword123')

    # Own PDF
    res_own_pdf = client.get('/students/STU_1001/report/pdf')
    assert res_own_pdf.status_code == 200
    assert res_own_pdf.headers["Content-Type"] == "application/pdf"

    # Other student's PDF -> 403 Forbidden
    res_other_pdf = client.get('/students/STU_1002/report/pdf')
    assert res_other_pdf.status_code == 403
