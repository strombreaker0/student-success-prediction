"""
End-to-End System Integration Test.
Verifies the complete workflow:
1. Database initialization and CSV data seeding
2. User registration and role enforcement (Admin, Faculty, Student)
3. Student record operations (Search, Add, Edit, Delete, Export)
4. ML model inference and prediction history persistence
5. Batch screening with schema validation
6. Student privacy isolation (preventing cross-student profile access)
"""

import os
import tempfile
import pandas as pd
from src.db.connection import get_db_connection
from src.db.schema import create_schema
from src.db.migrate import migrate_csv_to_sqlite
from src.services.auth_service import (
    register_user, authenticate_user, can_view_student,
    can_manage_students, can_delete_student
)
from src.services.student_service import (
    add_student, update_student, delete_student, get_student_by_id,
    list_students, export_students_to_csv, get_dashboard_summary_metrics
)
from src.services.prediction_service import (
    predict_student, get_prediction_history, run_batch_screening
)


def test_full_system_lifecycle():
    # 1. Initialize temporary SQLite database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = get_db_connection(db_path)
    create_schema(conn)

    # Migrate initial records from student_data.csv
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "student_data.csv")
    mig_res = migrate_csv_to_sqlite(csv_path=csv_path, conn=conn)
    assert mig_res["total_in_db"] == 1200

    # 2. Register Accounts
    # Admin
    ok_a, _, admin_u = register_user("admin_user", "admin@inst.edu", "AdminPass123", "admin", "System Admin", conn=conn)
    assert ok_a is True

    # Faculty
    ok_f, _, faculty_u = register_user("prof_patil", "patil@inst.edu", "ProfPass123", "faculty", "Prof. Patil", conn=conn)
    assert ok_f is True

    # Student linked to STU_1000
    ok_s, _, student_u = register_user("stu_asmita", "asmita@inst.edu", "StuPass123", "student", "Asmita Kumbar", linked_student_id="STU_1000", conn=conn)
    assert ok_s is True

    # 3. Authentication & Login
    auth_ok, _, logged_admin = authenticate_user("admin_user", "AdminPass123", conn=conn)
    assert auth_ok is True
    assert logged_admin["role"] == "admin"

    auth_stu_ok, _, logged_stu = authenticate_user("stu_asmita", "StuPass123", conn=conn)
    assert auth_stu_ok is True
    assert logged_stu["linked_student_id"] == "STU_1000"

    # 4. Role Permissions & Privacy Enforcement
    # Student can view their own profile STU_1000
    assert can_view_student(logged_stu, "STU_1000") is True
    # Student CANNOT view another student STU_1001
    assert can_view_student(logged_stu, "STU_1001") is False

    # Student listing students only returns their linked profile
    stu_view, stu_count = list_students(requesting_user=logged_stu, conn=conn)
    assert stu_count == 1
    assert stu_view[0]["student_id"] == "STU_1000"

    # 5. Student CRUD by Faculty & Admin
    new_student = {
        "student_id": "STU_TEST_E2E",
        "attendance_rate": 82.5,
        "study_hours_per_week": 16.0,
        "previous_scores": 72.0,
        "assignment_completion_rate": 88.0,
        "tutoring_sessions": 3,
        "sleep_hours": 7.5,
        "extracurricular": 1,
        "internet_access": 1,
        "final_exam_score": 64.0,
        "passed": 1
    }
    # Faculty adds student
    ok_add, _, created = add_student(new_student, requesting_user=faculty_u, conn=conn)
    assert ok_add is True
    assert created["student_id"] == "STU_TEST_E2E"

    # Faculty edits student
    ok_upd, _, updated = update_student("STU_TEST_E2E", dict(new_student, attendance_rate=89.0), requesting_user=faculty_u, conn=conn)
    assert ok_upd is True
    assert updated["attendance_rate"] == 89.0

    # Faculty tries to delete -> Denied
    ok_del_f, _ = delete_student("STU_TEST_E2E", requesting_user=faculty_u, conn=conn)
    assert ok_del_f is False

    # 6. ML Model Inference & Prediction History Logging
    pred_res = predict_student(
        student_data=updated,
        model_name="Logistic Regression",
        actor_username=faculty_u["username"],
        save_history=True,
        conn=conn
    )
    assert pred_res["predicted_outcome"] in (0, 1)
    assert 0.0 <= pred_res["pass_probability"] <= 1.0
    assert pred_res["risk_category"] in ("Low Risk", "Moderate Risk", "High Risk")
    assert len(pred_res["interventions"]) > 0

    # Verify history logged
    hist = get_prediction_history(student_id="STU_TEST_E2E", conn=conn)
    assert len(hist) == 1
    assert hist[0]["predicted_by"] == "prof_patil"

    # Admin deletes student -> Success
    ok_del_a, _ = delete_student("STU_TEST_E2E", requesting_user=admin_u, conn=conn)
    assert ok_del_a is True
    assert get_student_by_id("STU_TEST_E2E", conn=conn) is None

    # Prediction history should cascade-delete
    hist_after = get_prediction_history(student_id="STU_TEST_E2E", conn=conn)
    assert len(hist_after) == 0

    # 7. Batch Screening
    batch_df = pd.DataFrame([
        {"student_id": "S1", "attendance_rate": 90.0, "study_hours_per_week": 18.0, "previous_scores": 80.0,
         "assignment_completion_rate": 95.0, "tutoring_sessions": 2, "sleep_hours": 7.5, "extracurricular": 1, "internet_access": 1},
        {"student_id": "S2", "attendance_rate": 50.0, "study_hours_per_week": 5.0, "previous_scores": 40.0,
         "assignment_completion_rate": 45.0, "tutoring_sessions": 0, "sleep_hours": 5.0, "extracurricular": 0, "internet_access": 0}
    ])
    screened_df, errs = run_batch_screening(batch_df, model_name="Logistic Regression")
    assert len(errs) == 0
    assert len(screened_df) == 2
    assert "Risk_Level" in screened_df.columns

    # 8. CSV Export
    csv_str = export_students_to_csv(requesting_user=admin_u, conn=conn)
    assert "STU_1000" in csv_str
    assert "attendance_rate" in csv_str

    # 9. Dashboard metrics
    metrics = get_dashboard_summary_metrics(conn=conn)
    assert metrics["total_students"] == 1200
    assert metrics["passed_count"] > 0
    assert metrics["failed_count"] > 0

    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)
