"""
Unit and integration tests for Four-Year Academic Progress History,
semester results, subject grading, activities, RBAC isolation,
and PDF/CSV transcript generation.
"""

import os
import tempfile
import pytest
from src.db.connection import get_db_connection
from src.db.schema import create_schema
from src.services.academic_history_service import (
    get_student_academic_history, upsert_semester_record,
    add_subject_result, delete_subject_result,
    add_student_activity, delete_student_activity,
    export_academic_transcript_csv, generate_academic_transcript_pdf,
    get_year_for_semester, compute_grade_point
)
from src.services.prediction_service import predict_student


@pytest.fixture
def acad_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = get_db_connection(path)
    create_schema(conn)

    # Insert sample student
    conn.execute("""
    INSERT INTO students (
        student_id, attendance_rate, study_hours_per_week, previous_scores,
        assignment_completion_rate, tutoring_sessions, sleep_hours,
        extracurricular, internet_access, final_exam_score, passed
    ) VALUES ('STU_ACAD100', 84.0, 15.0, 72.0, 90.0, 2, 7.0, 1, 1, 65.0, 1);
    """)

    # Insert second student for privacy tests
    conn.execute("""
    INSERT INTO students (
        student_id, attendance_rate, study_hours_per_week, previous_scores,
        assignment_completion_rate, tutoring_sessions, sleep_hours,
        extracurricular, internet_access, final_exam_score, passed
    ) VALUES ('STU_ACAD200', 60.0, 8.0, 45.0, 50.0, 0, 6.0, 0, 1, 40.0, 0);
    """)
    conn.commit()

    yield conn, path

    conn.close()
    if os.path.exists(path):
        os.remove(path)


def test_semester_to_year_mapping():
    assert get_year_for_semester(1) == 1
    assert get_year_for_semester(2) == 1
    assert get_year_for_semester(3) == 2
    assert get_year_for_semester(4) == 2
    assert get_year_for_semester(5) == 3
    assert get_year_for_semester(6) == 3
    assert get_year_for_semester(7) == 4
    assert get_year_for_semester(8) == 4

    with pytest.raises(ValueError):
        get_year_for_semester(9)

    with pytest.raises(ValueError):
        get_year_for_semester(0)


def test_grade_point_computation():
    assert compute_grade_point("O") == 10.0
    assert compute_grade_point("A+") == 9.0
    assert compute_grade_point("A") == 8.0
    assert compute_grade_point("B+") == 7.0
    assert compute_grade_point("B") == 6.0
    assert compute_grade_point("F") == 0.0


def test_empty_academic_history(acad_db):
    conn, _ = acad_db
    faculty_user = {"role": "faculty", "username": "prof_test"}

    # Retrieve history when no semesters entered yet
    history = get_student_academic_history("STU_ACAD100", requesting_user=faculty_user, conn=conn)
    assert history is not None
    assert len(history["years"]) == 4
    assert len(history["all_semesters"]) == 8

    # All semesters should have 'Not Recorded' status
    for sem in history["all_semesters"]:
        assert sem["status"] == "Not Recorded"
        assert len(sem["subjects"]) == 0

    analytics = history["analytics"]
    assert analytics["overall_cgpa"] is None
    assert analytics["completed_semesters_count"] == 0
    assert analytics["total_credits_earned"] == 0.0


def test_semester_validation_and_upsert(acad_db):
    conn, _ = acad_db
    faculty_user = {"role": "faculty", "username": "prof_test"}
    student_user = {"role": "student", "linked_student_id": "STU_ACAD100"}

    # Student cannot enter semester results
    ok_stu, msg_stu, _ = upsert_semester_record(
        student_id="STU_ACAD100",
        semester_number=1,
        status="Passed",
        sgpa=8.5,
        requesting_user=student_user,
        conn=conn
    )
    assert ok_stu is False
    assert "Permission denied" in msg_stu

    # Invalid semester number
    ok_inv, msg_inv, _ = upsert_semester_record(
        student_id="STU_ACAD100",
        semester_number=12,
        status="Passed",
        requesting_user=faculty_user,
        conn=conn
    )
    assert ok_inv is False
    assert "Invalid semester" in msg_inv

    # Invalid SGPA (> 10)
    ok_sgpa, msg_sgpa, _ = upsert_semester_record(
        student_id="STU_ACAD100",
        semester_number=1,
        sgpa=11.5,
        requesting_user=faculty_user,
        conn=conn
    )
    assert ok_sgpa is False
    assert "SGPA must be between" in msg_sgpa

    # Valid Faculty entry for Semester 1
    ok_valid, msg_valid, sem_rec = upsert_semester_record(
        student_id="STU_ACAD100",
        semester_number=1,
        status="Passed",
        sgpa=8.25,
        total_credits=20.0,
        credits_earned=20.0,
        attendance_rate=88.5,
        assignment_rate=92.0,
        remarks="Excellent start",
        requesting_user=faculty_user,
        conn=conn
    )
    assert ok_valid is True
    assert sem_rec["semester_number"] == 1
    assert sem_rec["sgpa"] == 8.25

    # Valid Faculty entry for Semester 2
    ok2, _, _ = upsert_semester_record(
        student_id="STU_ACAD100",
        semester_number=2,
        status="Passed",
        sgpa=7.75,
        total_credits=22.0,
        credits_earned=22.0,
        attendance_rate=82.0,
        assignment_rate=85.0,
        requesting_user=faculty_user,
        conn=conn
    )
    assert ok2 is True


def test_subject_results_crud(acad_db):
    conn, _ = acad_db
    faculty_user = {"role": "faculty", "username": "prof_test"}

    # Add Subject 1
    ok1, msg1, sub1 = add_subject_result(
        student_id="STU_ACAD100",
        semester_number=1,
        subject_code="CS101",
        subject_name="Programming Principles",
        credits=4.0,
        internal_marks=19.0,
        external_marks=68.0,
        total_marks=87.0,
        grade="A+",
        status="Pass",
        requesting_user=faculty_user,
        conn=conn
    )
    assert ok1 is True
    assert sub1["subject_code"] == "CS101"
    assert sub1["grade_point"] == 9.0

    # Add Subject 2
    ok2, _, sub2 = add_subject_result(
        student_id="STU_ACAD100",
        semester_number=1,
        subject_code="MATH101",
        subject_name="Engineering Mathematics I",
        credits=4.0,
        internal_marks=15.0,
        external_marks=55.0,
        total_marks=70.0,
        grade="B+",
        status="Pass",
        requesting_user=faculty_user,
        conn=conn
    )
    assert ok2 is True

    # Check history includes subjects
    history = get_student_academic_history("STU_ACAD100", requesting_user=faculty_user, conn=conn)
    sem1 = history["all_semesters"][0]
    assert len(sem1["subjects"]) == 2

    # Delete subject
    ok_del, _ = delete_subject_result(sub2["id"], requesting_user=faculty_user, conn=conn)
    assert ok_del is True

    history_after = get_student_academic_history("STU_ACAD100", requesting_user=faculty_user, conn=conn)
    assert len(history_after["all_semesters"][0]["subjects"]) == 1


def test_student_activities_recording(acad_db):
    conn, _ = acad_db
    faculty_user = {"role": "faculty", "username": "prof_test"}

    ok_act, _, act = add_student_activity(
        student_id="STU_ACAD100",
        activity_type="Project",
        title="Smart Campus IoT Sensor Network",
        description="Designed MQTT sensor nodes for energy monitoring",
        organization_or_issuer="Department Research Lab",
        date_or_period="Spring 2024",
        outcome_or_award="Best Innovation Project",
        academic_year=1,
        skills_acquired="C++, ESP32, MQTT",
        requesting_user=faculty_user,
        conn=conn
    )
    assert ok_act is True
    assert act["title"] == "Smart Campus IoT Sensor Network"

    history = get_student_academic_history("STU_ACAD100", requesting_user=faculty_user, conn=conn)
    assert len(history["activities"]) == 1
    assert history["activities"][0]["activity_type"] == "Project"

    # Delete activity
    ok_del, _ = delete_student_activity(act["id"], requesting_user=faculty_user, conn=conn)
    assert ok_del is True


def test_progress_calculations_and_analytics(acad_db):
    conn, _ = acad_db
    faculty_user = {"role": "faculty", "username": "prof_test"}

    # Enter Semester 1 (SGPA: 8.0, 20 credits)
    upsert_semester_record(
        student_id="STU_ACAD100",
        semester_number=1,
        status="Passed",
        sgpa=8.0,
        total_credits=20.0,
        credits_earned=20.0,
        attendance_rate=90.0,
        assignment_rate=95.0,
        requesting_user=faculty_user,
        conn=conn
    )

    # Enter Semester 2 (SGPA: 9.0, 20 credits)
    upsert_semester_record(
        student_id="STU_ACAD100",
        semester_number=2,
        status="Passed",
        sgpa=9.0,
        total_credits=20.0,
        credits_earned=20.0,
        attendance_rate=80.0,
        assignment_rate=85.0,
        requesting_user=faculty_user,
        conn=conn
    )

    # Add subject with high grade
    add_subject_result(
        student_id="STU_ACAD100",
        semester_number=1,
        subject_code="CS101",
        subject_name="Data Structures",
        credits=4.0,
        total_marks=92.0,
        grade="O",
        status="Pass",
        requesting_user=faculty_user,
        conn=conn
    )

    history = get_student_academic_history("STU_ACAD100", requesting_user=faculty_user, conn=conn)
    analytics = history["analytics"]

    # CGPA should be (8.0 + 9.0) / 2 = 8.5
    assert analytics["overall_cgpa"] == 8.5
    assert analytics["total_credits_earned"] == 40.0
    assert analytics["completed_semesters_count"] == 2
    assert analytics["overall_attendance"] == 85.0
    assert len(analytics["strengths"]) > 0
    assert "Data Structures" in analytics["strengths"][0]


def test_student_isolation_and_privacy(acad_db):
    conn, _ = acad_db
    student_1 = {"role": "student", "username": "stu1", "linked_student_id": "STU_ACAD100"}
    student_2 = {"role": "student", "username": "stu2", "linked_student_id": "STU_ACAD200"}

    # Student 1 can view STU_ACAD100
    h1 = get_student_academic_history("STU_ACAD100", requesting_user=student_1, conn=conn)
    assert h1 is not None

    # Student 1 CANNOT view STU_ACAD200
    h2 = get_student_academic_history("STU_ACAD200", requesting_user=student_1, conn=conn)
    assert h2 is None

    # Student 2 CANNOT view STU_ACAD100
    h3 = get_student_academic_history("STU_ACAD100", requesting_user=student_2, conn=conn)
    assert h3 is None


def test_transcript_exports(acad_db):
    conn, _ = acad_db
    faculty_user = {"role": "faculty", "username": "prof_test"}

    # Add sample data
    upsert_semester_record(
        student_id="STU_ACAD100",
        semester_number=1,
        status="Passed",
        sgpa=8.0,
        total_credits=20.0,
        credits_earned=20.0,
        attendance_rate=90.0,
        requesting_user=faculty_user,
        conn=conn
    )

    # 1. Test CSV transcript export
    csv_str = export_academic_transcript_csv("STU_ACAD100", requesting_user=faculty_user, conn=conn)
    assert "Student_ID" in csv_str
    assert "STU_ACAD100" in csv_str
    assert "Semester 1" in csv_str

    # 2. Test PDF transcript export (ReportLab)
    pdf_bytes = generate_academic_transcript_pdf("STU_ACAD100", requesting_user=faculty_user, conn=conn)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 500
    # PDF magic header
    assert pdf_bytes.startswith(b"%PDF")


def test_ml_prediction_remains_functional(acad_db):
    conn, _ = acad_db
    faculty_user = {"role": "faculty", "username": "prof_test"}

    student_data = {
        "student_id": "STU_ACAD100",
        "attendance_rate": 84.0,
        "study_hours_per_week": 15.0,
        "previous_scores": 72.0,
        "assignment_completion_rate": 90.0,
        "tutoring_sessions": 2,
        "sleep_hours": 7.0,
        "extracurricular": 1,
        "internet_access": 1,
        "final_exam_score": 99.0,  # Should be ignored
        "passed": 1                # Should be ignored
    }

    pred_res = predict_student(
        student_data=student_data,
        model_name="Logistic Regression",
        actor_username=faculty_user["username"],
        save_history=True,
        conn=conn
    )
    assert pred_res["predicted_outcome"] in (0, 1)
    assert 0.0 <= pred_res["pass_probability"] <= 1.0
    assert pred_res["risk_category"] in ("Low Risk", "Moderate Risk", "High Risk")
