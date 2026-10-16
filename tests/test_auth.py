"""
Unit and integration tests for Authentication and RBAC Service.
"""

import os
import tempfile
import pytest
from src.db.connection import get_db_connection
from src.db.schema import create_schema
from src.services.auth_service import (
    hash_password, verify_password,
    validate_username, validate_email, validate_password_strength,
    validate_registration, register_user, authenticate_user,
    has_admin_user, create_session, is_session_expired,
    can_view_student, can_manage_students, can_delete_student, can_manage_users
)


@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = get_db_connection(path)
    create_schema(conn)

    # Insert a dummy student for student linkage tests
    conn.execute("""
    INSERT INTO students (
        student_id, attendance_rate, study_hours_per_week, previous_scores,
        assignment_completion_rate, tutoring_sessions, sleep_hours,
        extracurricular, internet_access, final_exam_score, passed
    ) VALUES ('STU_TEST01', 85.0, 15.0, 70.0, 90.0, 2, 7.0, 1, 1, 60.0, 1);
    """)
    conn.commit()

    yield conn, path

    conn.close()
    if os.path.exists(path):
        os.remove(path)


def test_password_hashing():
    pwd = "SecurePassword123"
    h = hash_password(pwd)
    assert h != pwd
    assert verify_password(h, pwd) is True
    assert verify_password(h, "WrongPassword123") is False
    assert verify_password("", pwd) is False
    assert verify_password(h, "") is False


def test_validation_helpers():
    # Username
    assert validate_username("asmita")[0] is True
    assert validate_username("a")[0] is False  # too short
    assert validate_username("bad user")[0] is False  # spaces

    # Email
    assert validate_email("asmita@institution.edu")[0] is True
    assert validate_email("invalid-email")[0] is False

    # Password
    assert validate_password_strength("Short1")[0] is False  # < 8 chars
    assert validate_password_strength("nocapitaldigit")[0] is False  # no digit
    assert validate_password_strength("ValidPass123")[0] is True


def test_user_registration_and_authentication(test_db):
    conn, _ = test_db

    # Register admin
    ok, msg, admin_user = register_user(
        username="admin1",
        email="admin@test.edu",
        password="AdminPassword123",
        role="admin",
        full_name="Admin User",
        conn=conn
    )
    assert ok is True
    assert admin_user["username"] == "admin1"
    assert admin_user["role"] == "admin"

    # Authenticate by username
    auth_ok, auth_msg, user = authenticate_user("admin1", "AdminPassword123", conn=conn)
    assert auth_ok is True
    assert user["email"] == "admin@test.edu"

    # Authenticate by email
    auth_ok, auth_msg, user = authenticate_user("admin@test.edu", "AdminPassword123", conn=conn)
    assert auth_ok is True

    # Bad password
    bad_ok, bad_msg, _ = authenticate_user("admin1", "WrongPassword", conn=conn)
    assert bad_ok is False

    # Duplicate username should fail
    dup_ok, dup_msg, _ = register_user(
        username="admin1",
        email="another@test.edu",
        password="AnotherPassword123",
        role="faculty",
        full_name="Another User",
        conn=conn
    )
    assert dup_ok is False
    assert "already taken" in dup_msg


def test_student_role_linking(test_db):
    conn, _ = test_db

    # Student without linked_student_id should fail
    ok, msg, _ = register_user(
        username="student1",
        email="student1@test.edu",
        password="StudentPassword123",
        role="student",
        full_name="Student One",
        linked_student_id=None,
        conn=conn
    )
    assert ok is False
    assert "linked" in msg.lower()

    # Student with non-existent student_id should fail
    ok, msg, _ = register_user(
        username="student1",
        email="student1@test.edu",
        password="StudentPassword123",
        role="student",
        full_name="Student One",
        linked_student_id="NON_EXISTENT",
        conn=conn
    )
    assert ok is False
    assert "not found" in msg.lower()

    # Student with valid student_id should succeed
    ok, msg, stu_user = register_user(
        username="student1",
        email="student1@test.edu",
        password="StudentPassword123",
        role="student",
        full_name="Student One",
        linked_student_id="STU_TEST01",
        conn=conn
    )
    assert ok is True
    assert stu_user["linked_student_id"] == "STU_TEST01"

    # Second student trying to link to same student_id should fail
    ok2, msg2, _ = register_user(
        username="student2",
        email="student2@test.edu",
        password="StudentPassword123",
        role="student",
        full_name="Student Two",
        linked_student_id="STU_TEST01",
        conn=conn
    )
    assert ok2 is False
    assert "already linked" in msg2.lower()


def test_rbac_permissions():
    admin = {"id": 1, "username": "admin", "role": "admin", "linked_student_id": None}
    faculty = {"id": 2, "username": "prof", "role": "faculty", "linked_student_id": None}
    student_a = {"id": 3, "username": "stuA", "role": "student", "linked_student_id": "STU_1000"}

    # can_view_student
    assert can_view_student(admin, "STU_1000") is True
    assert can_view_student(faculty, "STU_1000") is True
    assert can_view_student(student_a, "STU_1000") is True
    # Student CANNOT view another student's profile
    assert can_view_student(student_a, "STU_9999") is False

    # can_manage_students (Add / Edit)
    assert can_manage_students(admin) is True
    assert can_manage_students(faculty) is True
    assert can_manage_students(student_a) is False

    # can_delete_student (Admin only)
    assert can_delete_student(admin) is True
    assert can_delete_student(faculty) is False
    assert can_delete_student(student_a) is False

    # can_manage_users (Admin only)
    assert can_manage_users(admin) is True
    assert can_manage_users(faculty) is False
    assert can_manage_users(student_a) is False


def test_session_lifecycle():
    user = {"id": 1, "username": "testuser", "role": "faculty"}
    session = create_session(user)
    assert session["user"]["username"] == "testuser"
    assert is_session_expired(session, timeout_minutes=60) is False

    # Fake expired session
    session["last_activity"] = "2000-01-01T00:00:00+00:00"
    assert is_session_expired(session, timeout_minutes=60) is True
