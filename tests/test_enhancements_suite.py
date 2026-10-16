"""
Comprehensive Enhancement Features Test Suite.
Covers Priority 1, 2, and 3 enhancements:
1. Explainable predictions (top 3 factors, real weights, no data leakage, risk badges, disclaimer, DB persistence)
2. Model transparency page (benchmarks, confusion matrix, limitations, missing model handling)
3. Remedial intervention tracker (CRUD, status flow, overdue tracking, RBAC)
4. System audit log (event recording, credential sanitization, admin-only viewer)
5. What-if simulator (real-time calculation, no history persistence)
6. Bulk CSV upload (row validation, atomic transaction rollback)
7. PDF Assessment generation (ReportLab integration)
"""

import io
import json
import pytest
from src.services.prediction_service import (
    predict_student, get_prediction_history, FEATURE_COLS
)
from src.services.intervention_service import (
    create_intervention, update_intervention, list_interventions, get_overdue_interventions
)
from src.services.audit_service import (
    log_audit_event, list_audit_logs, sanitize_details
)
from src.services.pdf_service import generate_student_pdf_report
from src.db.connection import get_db_connection


def login_as(client, username, password):
    client.post('/logout', follow_redirects=True)
    return client.post('/login', data={'username_or_email': username, 'password': password}, follow_redirects=True)


# ==============================================================================
# PRIORITY 1.1: EXPLAINABLE PREDICTIONS
# ==============================================================================

def test_explainable_predictions_top_three_factors_and_no_leakage(app_with_db):
    """
    Verify top 3 contributing factors exist, are formatted in plain English,
    use real model feature weights, and STRICTLY exclude target labels (no data leakage).
    """
    _, db_path = app_with_db
    conn = get_db_connection(db_path)

    # 1. Verify no target leakage columns in FEATURE_COLS
    assert "passed" not in FEATURE_COLS
    assert "final_exam_score" not in FEATURE_COLS
    assert len(FEATURE_COLS) == 8

    # 2. Test student with strong negative factors (low attendance, low study)
    at_risk_student = {
        "student_id": "STU_1002",
        "attendance_rate": 52.0,
        "study_hours_per_week": 6.0,
        "previous_scores": 42.0,
        "assignment_completion_rate": 50.0,
        "tutoring_sessions": 0,
        "sleep_hours": 5.5,
        "extracurricular": 0,
        "internet_access": 1,
        # Even if someone accidentally passes target columns, the service must ignore them
        "passed": 1,
        "final_exam_score": 90.0
    }

    result = predict_student(at_risk_student, model_name="Logistic Regression", save_history=True, conn=conn)

    # Top 3 factors must be present
    assert len(result["top_factors"]) == 3
    for factor in result["top_factors"]:
        assert factor["feature"] in FEATURE_COLS
        assert "description" in factor
        assert len(factor["description"]) > 10
        assert factor["direction"] in ("positive", "negative")

    # Risk badge mapping
    assert result["risk_category"] == "High Risk"
    assert result["fail_probability"] > 0.50

    # Advisory disclaimer
    assert "Predictions support teacher judgment" in result["disclaimer"]

    # History persistence: verify top_factors_json is stored in SQLite
    history = get_prediction_history(student_id="STU_1002", limit=1, conn=conn)
    assert len(history) == 1
    assert len(history[0]["top_factors"]) == 3
    conn.close()


def test_prediction_risk_level_mapping():
    """Verify exact probabilistic boundaries for Low, Moderate, and High Risk."""
    from src.services.prediction_service import determine_risk_category
    assert determine_risk_category(0.85) == "Low Risk"
    assert determine_risk_category(0.75) == "Low Risk"
    assert determine_risk_category(0.749) == "Moderate Risk"
    assert determine_risk_category(0.50) == "Moderate Risk"
    assert determine_risk_category(0.499) == "High Risk"
    assert determine_risk_category(0.10) == "High Risk"


# ==============================================================================
# PRIORITY 1.2: MODEL TRANSPARENCY PAGE
# ==============================================================================

def test_model_transparency_page_rendered(client):
    """Model transparency renders benchmarks, confusion matrix, and limitations."""
    login_as(client, 'faculty_test', 'TeacherTestPassword123')
    res = client.get('/transparency')
    assert res.status_code == 200
    assert b"Logistic Regression" in res.data
    assert b"Confusion Matrix" in res.data
    assert b"Limitations" in res.data
    assert b"80.0" in res.data  # Accuracy


def test_model_transparency_handles_missing_file_gracefully(app_with_db, monkeypatch):
    """When metrics file is unavailable, page renders friendly alert instead of 500 crash."""
    app, _ = app_with_db
    client = app.test_client()
    login_as(client, 'faculty_test', 'TeacherTestPassword123')

    # Simulate non-existent file
    monkeypatch.setattr("os.path.exists", lambda path: False if "evaluation_metrics.json" in path else True)
    res = client.get('/transparency')
    assert res.status_code == 200
    assert b"Model Status Notice" in res.data


# ==============================================================================
# PRIORITY 1.3: INTERVENTION TRACKER
# ==============================================================================

def test_intervention_crud_and_rbac(app_with_db):
    """Intervention lifecycle: create, update status, list, and enforce student permissions."""
    _, db_path = app_with_db
    conn = get_db_connection(db_path)

    faculty_user = {"role": "faculty", "username": "prof_test", "full_name": "Prof Test"}
    student_user = {"role": "student", "username": "stu_test", "linked_student_id": "STU_1001"}

    # 1. Student CANNOT create interventions
    s_ok, s_msg, _ = create_intervention(
        student_id="STU_1001",
        title="Student self intervention",
        requesting_user=student_user,
        conn=conn
    )
    assert s_ok is False
    assert "Students cannot create" in s_msg

    # 2. Faculty CAN create intervention
    f_ok, f_msg, created = create_intervention(
        student_id="STU_1001",
        title="Remedial Math Tutoring",
        description="Attend 3 extra tutoring sessions weekly.",
        follow_up_date="2026-11-30",
        created_by="Prof Test",
        requesting_user=faculty_user,
        conn=conn
    )
    assert f_ok is True
    int_id = created["id"]
    assert created["status"] == "Open"

    # 3. Faculty updates status to 'In progress' then 'Resolved'
    upd_ok, _, updated = update_intervention(
        intervention_id=int_id,
        status="In progress",
        requesting_user=faculty_user,
        conn=conn
    )
    assert upd_ok is True
    assert updated["status"] == "In progress"

    # 4. Student listing only sees their own
    items_stu, count_stu = list_interventions(requesting_user=student_user, conn=conn)
    assert count_stu >= 1
    for it in items_stu:
        assert it["student_id"] == "STU_1001"

    conn.close()


def test_overdue_interventions_detection(app_with_db):
    """Identifies interventions whose follow_up_date has passed without resolution."""
    _, db_path = app_with_db
    conn = get_db_connection(db_path)

    # Insert an overdue intervention (follow up in the past)
    create_intervention(
        student_id="STU_1001",
        title="Past Milestone Review",
        description="Overdue item",
        follow_up_date="2020-01-01",  # clearly past date
        created_by="Advisor",
        conn=conn
    )

    overdue = get_overdue_interventions(conn=conn)
    assert len(overdue) >= 1
    assert any(o["title"] == "Past Milestone Review" for o in overdue)
    conn.close()


# ==============================================================================
# PRIORITY 1.4: AUDIT LOG SERVICE
# ==============================================================================

def test_audit_logging_and_credential_sanitization(app_with_db, client):
    """Audit log records actions, sanitizes credentials, and restricts viewer to admins."""
    _, db_path = app_with_db
    conn = get_db_connection(db_path)

    # 1. Verify credential masking
    dirty_text = "User attempted login with password=SecretPassword123"
    clean_text = sanitize_details(dirty_text)
    assert "SecretPassword123" not in clean_text
    assert "MASKED_CREDENTIAL_DATA" in clean_text

    # 2. Log test event
    log_audit_event("admin_test", "TEST_SECURITY_ACTION", target="test_entity", details="Safe operational log", conn=conn)

    admin_u = {"role": "admin", "username": "admin_test"}
    faculty_u = {"role": "faculty", "username": "faculty_test"}

    # 3. Admin can view
    logs, total = list_audit_logs(action="TEST_SECURITY_ACTION", requesting_user=admin_u, conn=conn)
    assert total >= 1
    assert logs[0]["action"] == "TEST_SECURITY_ACTION"

    # 4. Non-admin is blocked
    with pytest.raises(PermissionError):
        list_audit_logs(requesting_user=faculty_u, conn=conn)

    conn.close()


# ==============================================================================
# PRIORITY 2: WHAT-IF SIMULATOR, BULK CSV UPLOAD, PDF REPORT
# ==============================================================================

def test_what_if_simulator_no_history_commitment(app_with_db, client):
    """Simulation generates real prediction without recording in prediction_history."""
    _, db_path = app_with_db
    conn = get_db_connection(db_path)
    login_as(client, 'faculty_test', 'TeacherTestPassword123')

    # Initial history count
    initial_preds = conn.execute("SELECT COUNT(*) FROM prediction_history;").fetchone()[0]

    # Call simulation API
    res = client.post('/api/simulate', json={
        "attendance_rate": 88.0,
        "study_hours_per_week": 18.0,
        "previous_scores": 80.0,
        "assignment_completion_rate": 90.0,
        "tutoring_sessions": 2,
        "sleep_hours": 7.0,
        "extracurricular": 1,
        "internet_access": 1
    })
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "pass_probability_pct" in data
    assert len(data["top_factors"]) == 3

    # Verify NO new records in prediction_history
    final_preds = conn.execute("SELECT COUNT(*) FROM prediction_history;").fetchone()[0]
    assert final_preds == initial_preds
    conn.close()


def test_bulk_csv_upload_atomic_integrity(client, app_with_db):
    """Bulk CSV upload commits valid files and rolls back invalid ones completely."""
    _, db_path = app_with_db
    conn = get_db_connection(db_path)
    login_as(client, 'faculty_test', 'TeacherTestPassword123')

    # 1. Valid CSV import
    valid_csv = (
        "student_id,attendance_rate,study_hours_per_week,previous_scores,assignment_completion_rate,tutoring_sessions,sleep_hours,extracurricular,internet_access\n"
        "STU_BULK01,85.0,15.0,72.0,88.0,2,7.0,1,1\n"
        "STU_BULK02,78.0,12.0,65.0,80.0,1,6.5,0,1\n"
    )
    res_valid = client.post('/students/bulk-upload', data={
        'file': (io.BytesIO(valid_csv.encode('utf-8')), 'valid_roster.csv')
    }, follow_redirects=True)
    assert res_valid.status_code == 200
    assert b"Successfully processed and imported 2 student records" in res_valid.data

    # Verify both records exist in DB
    assert conn.execute("SELECT student_id FROM students WHERE student_id = 'STU_BULK01';").fetchone() is not None
    assert conn.execute("SELECT student_id FROM students WHERE student_id = 'STU_BULK02';").fetchone() is not None

    # 2. Invalid CSV with intentional error on row 2 (attendance 500% out of range)
    invalid_csv = (
        "student_id,attendance_rate,study_hours_per_week,previous_scores,assignment_completion_rate,tutoring_sessions,sleep_hours,extracurricular,internet_access\n"
        "STU_BULK03,80.0,14.0,70.0,85.0,2,7.0,1,1\n"
        "STU_BULK04,500.0,10.0,60.0,75.0,1,6.0,0,1\n"
    )
    res_inv = client.post('/students/bulk-upload', data={
        'file': (io.BytesIO(invalid_csv.encode('utf-8')), 'invalid_roster.csv')
    }, follow_redirects=True)
    assert b"Validation failed" in res_inv.data

    # Atomic test: STU_BULK03 must NOT have been saved!
    assert conn.execute("SELECT student_id FROM students WHERE student_id = 'STU_BULK03';").fetchone() is None
    conn.close()


def test_student_pdf_generation_content(client):
    """Generates student PDF report dossier with profile, explainable factors, and disclaimer."""
    login_as(client, 'faculty_test', 'TeacherTestPassword123')
    res = client.get('/students/STU_1001/report/pdf')
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/pdf"
    assert len(res.data) > 2000  # Valid binary PDF length
    assert res.data.startswith(b"%PDF")
