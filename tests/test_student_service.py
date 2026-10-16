"""
Unit and integration tests for Student Management Service.
"""

import os
import tempfile
import pytest
from src.db.connection import get_db_connection
from src.db.schema import create_schema
from src.services.student_service import (
    validate_student_record, add_student, update_student,
    delete_student, get_student_by_id, list_students,
    export_students_to_csv, get_dashboard_summary_metrics
)


@pytest.fixture
def student_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = get_db_connection(path)
    create_schema(conn)

    # Insert sample students
    sample_students = [
        ("STU_1001", 85.0, 15.0, 75.0, 90.0, 2, 7.5, 1, 1, 65.0, 1),
        ("STU_1002", 60.0, 8.0, 45.0, 50.0, 0, 5.5, 0, 1, 38.0, 0),
        ("STU_1003", 92.0, 20.0, 88.0, 95.0, 4, 8.0, 1, 1, 80.0, 1),
    ]
    for s in sample_students:
        conn.execute("""
        INSERT INTO students (
            student_id, attendance_rate, study_hours_per_week, previous_scores,
            assignment_completion_rate, tutoring_sessions, sleep_hours,
            extracurricular, internet_access, final_exam_score, passed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, s)
    conn.commit()

    yield conn, path

    conn.close()
    if os.path.exists(path):
        os.remove(path)


def test_validation_ranges(student_db):
    conn, _ = student_db

    valid_data = {
        "student_id": "STU_NEW01",
        "attendance_rate": 80.0,
        "study_hours_per_week": 14.0,
        "previous_scores": 65.0,
        "assignment_completion_rate": 85.0,
        "tutoring_sessions": 2,
        "sleep_hours": 7.0,
        "extracurricular": 1,
        "internet_access": 1
    }
    assert validate_student_record(valid_data, is_new=True, conn=conn)[0] is True

    # Out of range attendance (> 100)
    bad_data = dict(valid_data, attendance_rate=105.0)
    ok, msg = validate_student_record(bad_data, is_new=True, conn=conn)
    assert ok is False
    assert "attendance_rate" in msg

    # Negative study hours
    bad_data = dict(valid_data, study_hours_per_week=-2.0)
    ok, msg = validate_student_record(bad_data, is_new=True, conn=conn)
    assert ok is False

    # Duplicate student ID
    dup_data = dict(valid_data, student_id="STU_1001")
    ok, msg = validate_student_record(dup_data, is_new=True, conn=conn)
    assert ok is False
    assert "already exists" in msg


def test_add_and_update_student(student_db):
    conn, _ = student_db
    faculty_user = {"role": "faculty", "username": "dr_smith"}
    student_user = {"role": "student", "username": "stu_john"}

    new_data = {
        "student_id": "STU_9999",
        "attendance_rate": 78.5,
        "study_hours_per_week": 12.0,
        "previous_scores": 70.0,
        "assignment_completion_rate": 82.0,
        "tutoring_sessions": 1,
        "sleep_hours": 6.5,
        "extracurricular": 0,
        "internet_access": 1,
        "final_exam_score": 55.0,
        "passed": 1
    }

    # Student cannot add records
    ok, msg, _ = add_student(new_data, requesting_user=student_user, conn=conn)
    assert ok is False
    assert "Permission denied" in msg

    # Faculty can add records
    ok, msg, created = add_student(new_data, requesting_user=faculty_user, conn=conn)
    assert ok is True
    assert created["student_id"] == "STU_9999"

    # Update record
    updated_data = dict(new_data, attendance_rate=88.0)
    ok, msg, updated = update_student("STU_9999", updated_data, requesting_user=faculty_user, conn=conn)
    assert ok is True
    assert updated["attendance_rate"] == 88.0


def test_delete_student_authorization(student_db):
    conn, _ = student_db
    admin_user = {"role": "admin", "username": "superadmin"}
    faculty_user = {"role": "faculty", "username": "faculty1"}

    # Faculty cannot delete
    ok, msg = delete_student("STU_1001", requesting_user=faculty_user, conn=conn)
    assert ok is False
    assert "Administrator" in msg

    # Admin can delete
    ok, msg = delete_student("STU_1001", requesting_user=admin_user, conn=conn)
    assert ok is True
    assert get_student_by_id("STU_1001", conn=conn) is None


def test_list_and_filter_students(student_db):
    conn, _ = student_db
    admin_user = {"role": "admin"}
    student_user = {"role": "student", "linked_student_id": "STU_1002"}

    # Admin lists all 3
    recs, total = list_students(requesting_user=admin_user, conn=conn)
    assert total == 3
    assert len(recs) == 3

    # Filter by passed
    passed_recs, passed_total = list_students(outcome_filter="Passed", requesting_user=admin_user, conn=conn)
    assert passed_total == 2

    # Filter by failed
    failed_recs, failed_total = list_students(outcome_filter="Failed", requesting_user=admin_user, conn=conn)
    assert failed_total == 1

    # Student user sees ONLY their linked record
    stu_recs, stu_total = list_students(requesting_user=student_user, conn=conn)
    assert stu_total == 1
    assert stu_recs[0]["student_id"] == "STU_1002"


def test_csv_export_and_metrics(student_db):
    conn, _ = student_db
    admin_user = {"role": "admin"}

    csv_data = export_students_to_csv(requesting_user=admin_user, conn=conn)
    assert "student_id" in csv_data
    assert "STU_1001" in csv_data
    assert "STU_1002" in csv_data

    metrics = get_dashboard_summary_metrics(conn=conn)
    assert metrics["total_students"] == 3
    assert metrics["passed_count"] == 2
    assert metrics["failed_count"] == 1
    assert metrics["pass_rate"] == 66.7
