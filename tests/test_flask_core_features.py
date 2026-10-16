"""
Core Features, Database Integrity, CSRF, and Persistence Test Suite.
Tests:
- CSRF validation enforcement
- Database transaction integrity and rollback on error
- Data persistence across application reboots
- Prediction functionality with real models
- CSV and PDF reporting
"""

import pytest
from flask_app import create_app
from flask_app.config import TestingConfig
from src.db.connection import get_db_connection, get_db_context
from src.services.prediction_service import predict_student, get_prediction_history


def test_csrf_validation_enforcement(csrf_client):
    """CSRF Protection: POST request without valid CSRF token is rejected with 400."""
    res = csrf_client.post('/login', data={
        'username_or_email': 'admin_test',
        'password': 'AdminTestPassword123'
    })
    # Must fail with 400 Bad Request due to missing CSRF token
    assert res.status_code == 400


def test_db_transaction_rollback_on_error(app_with_db):
    """Database rollback: failed multi-step transaction rolls back cleanly without dirty writes."""
    _, db_path = app_with_db
    conn = get_db_connection(db_path)

    initial_count = conn.execute("SELECT COUNT(*) FROM students;").fetchone()[0]

    with pytest.raises(Exception):
        with get_db_context(db_path) as ctx_conn:
            # Step 1: Valid insert
            ctx_conn.execute("""
            INSERT INTO students (student_id, attendance_rate, study_hours_per_week)
            VALUES ('STU_TEMP_FAIL', 80.0, 10.0);
            """)
            # Step 2: Intentional constraint violation (negative attendance rate fails CHECK constraint)
            ctx_conn.execute("""
            INSERT INTO students (student_id, attendance_rate, study_hours_per_week)
            VALUES ('STU_ILLEGAL', -50.0, 10.0);
            """)

    # Verify transaction rolled back completely
    final_count = conn.execute("SELECT COUNT(*) FROM students;").fetchone()[0]
    assert final_count == initial_count

    # Verify STU_TEMP_FAIL was NOT saved
    assert conn.execute("SELECT student_id FROM students WHERE student_id = 'STU_TEMP_FAIL';").fetchone() is None
    conn.close()


def test_persistence_across_app_restarts(app_with_db):
    """Data persistence: records survive application shutdown and restart."""
    _, db_path = app_with_db

    # Step 1: Create a record with first app instance
    conn = get_db_connection(db_path)
    conn.execute("INSERT INTO students (student_id, attendance_rate, study_hours_per_week) VALUES ('STU_PERSIST', 95.0, 20.0);")
    conn.commit()
    conn.close()

    # Step 2: Spin up a brand new app factory instance pointing to the same db
    class RebootConfig(TestingConfig):
        STUDENT_DB_PATH = db_path
        WTF_CSRF_ENABLED = False

    rebooted_app = create_app(RebootConfig)
    reboot_client = rebooted_app.test_client()

    # Sign in as admin on the rebooted app
    reboot_client.post('/login', data={'username_or_email': 'admin_test', 'password': 'AdminTestPassword123'})
    res = reboot_client.get('/students/STU_PERSIST')
    assert res.status_code == 200
    assert b"STU_PERSIST" in res.data


def test_real_time_prediction_service():
    """Predictive inference pipeline uses real model and outputs probability and risk stratification."""
    input_data = {
        "student_id": "STU_EVAL_TEST",
        "attendance_rate": 85.0,
        "study_hours_per_week": 18.0,
        "previous_scores": 75.0,
        "assignment_completion_rate": 90.0,
        "tutoring_sessions": 3,
        "sleep_hours": 7.5,
        "extracurricular": 1,
        "internet_access": 1
    }

    res = predict_student(input_data, model_name="Logistic Regression", save_history=False)
    assert res["predicted_outcome"] in (0, 1)
    assert 0.0 <= res["pass_probability"] <= 1.0
    assert res["risk_category"] in ("Low Risk", "Moderate Risk", "High Risk")
    assert len(res["top_factors"]) == 3
    assert "Predictions support teacher judgment" in res["disclaimer"]


def test_dashboard_with_none_attendance_and_incomplete_records(app_with_db):
    """
    REGRESSION TEST: Fix TypeError '<' not supported between instances of 'NoneType' and 'float'.
    Ensures dashboard renders successfully when records have None attendance, study hours, or marks.
    """
    app, db_path = app_with_db
    conn = get_db_connection(db_path)
    try:
        # Insert student with NULL attendance and failed status (triggering the needs_attention query)
        conn.execute("""
        INSERT INTO students (student_id, attendance_rate, study_hours_per_week, previous_scores, passed)
        VALUES ('STU_NULL_ATT', NULL, NULL, NULL, 0);
        """)
        # Insert student with partial record
        conn.execute("""
        INSERT INTO students (student_id, attendance_rate, study_hours_per_week, previous_scores, passed)
        VALUES ('STU_PARTIAL_70', 68.5, 10.0, 55.0, NULL);
        """)
        conn.commit()
    finally:
        conn.close()

    client = app.test_client()
    # Login as faculty
    login_res = client.post('/login', data={'username_or_email': 'faculty_test', 'password': 'TeacherTestPassword123'}, follow_redirects=True)
    assert login_res.status_code == 200

    # Request dashboard
    dashboard_res = client.get('/dashboard')
    assert dashboard_res.status_code == 200
    assert b"STU_NULL_ATT" in dashboard_res.data
    assert b"Not Recorded" in dashboard_res.data


def test_dashboard_empty_database_graceful_handling(app_with_db):
    """
    Empty database resilience test:
    When zero student records exist, dashboard renders gracefully with empty states
    and honest N/A indicators, rather than crashing or falsifying 0.0% metrics.
    """
    app, db_path = app_with_db
    conn = get_db_connection(db_path)
    try:
        conn.execute("DELETE FROM students;")
        conn.commit()
    finally:
        conn.close()

    client = app.test_client()
    client.post('/login', data={'username_or_email': 'admin_test', 'password': 'AdminTestPassword123'}, follow_redirects=True)

    dashboard_res = client.get('/dashboard')
    assert dashboard_res.status_code == 200
    assert b"Executive Analytics Dashboard" in dashboard_res.data
    assert b"N/A" in dashboard_res.data

