"""
Pytest Fixtures for Flask Test Suite.
Creates isolated temporary databases for testing so production records are never touched.
"""

import os
import tempfile
import pytest
from flask_app import create_app
from flask_app.config import TestingConfig
from src.db.connection import get_db_connection
from src.db.schema import create_schema
from src.db.migrate_enhancements import run_enhancements_migration
from src.services.auth_service import register_user
from src.services.student_service import add_student


@pytest.fixture
def app_with_db():
    """
    Creates an isolated test application instance with a dedicated temporary SQLite DB.
    Seeds a test admin, faculty, student user, and dummy student records.
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Initialize tables
    conn = get_db_connection(db_path)
    create_schema(conn)
    run_enhancements_migration(conn)

    # Seed test student records
    sample_students = [
        {
            "student_id": "STU_1001",
            "attendance_rate": 88.0,
            "study_hours_per_week": 16.5,
            "previous_scores": 78.0,
            "assignment_completion_rate": 90.0,
            "tutoring_sessions": 2,
            "sleep_hours": 7.0,
            "extracurricular": 1,
            "internet_access": 1,
            "passed": 1,
            "final_exam_score": 75.0
        },
        {
            "student_id": "STU_1002",
            "attendance_rate": 52.0,
            "study_hours_per_week": 6.0,
            "previous_scores": 42.0,
            "assignment_completion_rate": 50.0,
            "tutoring_sessions": 0,
            "sleep_hours": 5.5,
            "extracurricular": 0,
            "internet_access": 1,
            "passed": 0,
            "final_exam_score": 38.0
        },
        {
            "student_id": "STU_1003",
            "attendance_rate": 75.0,
            "study_hours_per_week": 12.0,
            "previous_scores": 65.0,
            "assignment_completion_rate": 80.0,
            "tutoring_sessions": 1,
            "sleep_hours": 7.0,
            "extracurricular": 1,
            "internet_access": 1,
            "passed": 1,
            "final_exam_score": 68.0
        }
    ]
    for s in sample_students:
        add_student(s, conn=conn)

    # Seed test user accounts
    register_user(
        username="admin_test",
        email="admin@institution.edu",
        password="AdminTestPassword123",
        role="admin",
        full_name="System Administrator",
        conn=conn
    )
    register_user(
        username="faculty_test",
        email="teacher@institution.edu",
        password="TeacherTestPassword123",
        role="faculty",
        full_name="Prof. Sharma",
        conn=conn
    )
    register_user(
        username="student_test",
        email="student@institution.edu",
        password="StudentTestPassword123",
        role="student",
        full_name="Student Test",
        linked_student_id="STU_1001",
        conn=conn
    )
    conn.close()

    # Configure app for testing
    old_env = os.environ.get("STUDENT_DB_PATH")
    os.environ["STUDENT_DB_PATH"] = db_path

    class CustomTestingConfig(TestingConfig):
        STUDENT_DB_PATH = db_path
        WTF_CSRF_ENABLED = False
        SECRET_KEY = "test-secret-key-12345"

    app = create_app(CustomTestingConfig)

    yield app, db_path

    # Teardown
    if old_env is not None:
        os.environ["STUDENT_DB_PATH"] = old_env
    else:
        os.environ.pop("STUDENT_DB_PATH", None)

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.fixture
def client(app_with_db):
    app, _ = app_with_db
    return app.test_client()


@pytest.fixture
def csrf_client(app_with_db):
    """Client with CSRF enabled for testing CSRF validation."""
    app, _ = app_with_db
    app.config["WTF_CSRF_ENABLED"] = True
    return app.test_client()
