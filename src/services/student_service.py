"""
Student Management Service.
Handles student record CRUD operations, filtering, search, numeric range validations,
and CSV exports with role-based visibility rules.
"""

import io
import csv
from datetime import datetime, timezone
import pandas as pd
from src.db.connection import get_db_connection
from src.services.auth_service import can_view_student, can_manage_students, can_delete_student


def validate_student_record(data: dict, is_new: bool = False, conn = None) -> tuple[bool, str]:
    """
    Validates student attributes and numeric ranges.
    Returns (is_valid, error_message).
    """
    student_id = str(data.get("student_id", "")).strip().upper()
    if not student_id:
        return False, "Student ID is required."

    if is_new:
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT student_id FROM students WHERE student_id = ?;", (student_id,))
            if cursor.fetchone():
                return False, f"A student record with ID '{student_id}' already exists."
        finally:
            if close_conn:
                conn.close()

    # Numeric range validations
    def _check_range(field_name: str, val, min_v: float, max_v: float, allow_none: bool = False):
        if val is None or val == "":
            if allow_none:
                return True, ""
            return False, f"{field_name} is required."
        try:
            num = float(val)
            if num < min_v or num > max_v:
                return False, f"{field_name} must be between {min_v} and {max_v} (received {num})."
            return True, ""
        except (ValueError, TypeError):
            return False, f"{field_name} must be a valid number."

    ranges = [
        ("attendance_rate", data.get("attendance_rate"), 0.0, 100.0, False),
        ("study_hours_per_week", data.get("study_hours_per_week"), 0.0, 100.0, False),
        ("previous_scores", data.get("previous_scores"), 0.0, 100.0, False),
        ("assignment_completion_rate", data.get("assignment_completion_rate"), 0.0, 100.0, False),
        ("tutoring_sessions", data.get("tutoring_sessions"), 0.0, 50.0, False),
        ("sleep_hours", data.get("sleep_hours"), 0.0, 24.0, False),
        ("final_exam_score", data.get("final_exam_score"), 0.0, 100.0, True),
    ]

    for field, val, min_v, max_v, allow_none in ranges:
        ok, msg = _check_range(field, val, min_v, max_v, allow_none)
        if not ok:
            return False, msg

    # Binary flag checks
    extra = data.get("extracurricular")
    if extra not in (0, 1, "0", "1"):
        return False, "Extracurricular must be 0 (No) or 1 (Yes)."

    internet = data.get("internet_access")
    if internet not in (0, 1, "0", "1"):
        return False, "Internet access must be 0 (No) or 1 (Yes)."

    passed = data.get("passed")
    if passed is not None and passed != "" and passed not in (0, 1, "0", "1"):
        return False, "Passed status must be 0 (Fail) or 1 (Pass) or empty."

    return True, ""


def get_student_by_id(student_id: str, requesting_user: dict | None = None, conn = None) -> dict | None:
    """
    Retrieves a single student record with authorization checks.
    Students can only retrieve their own record.
    """
    if requesting_user and not can_view_student(requesting_user, student_id):
        return None

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = ?;", (student_id.strip().upper(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if close_conn:
            conn.close()


def list_students(
    search_query: str = "",
    outcome_filter: str = "All",
    requesting_user: dict | None = None,
    limit: int = 1000,
    offset: int = 0,
    conn = None
) -> tuple[list[dict], int]:
    """
    Lists students matching search and outcome criteria, enforcing RBAC.
    Returns (records, total_matching_count).
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        conditions = []
        params = []

        # Enforce student role isolation
        if requesting_user and requesting_user.get("role") == "student":
            sid = requesting_user.get("linked_student_id")
            if not sid:
                return [], 0
            conditions.append("student_id = ?")
            params.append(sid.strip().upper())
        else:
            # Search query
            if search_query and search_query.strip():
                clean_q = f"%{search_query.strip().upper()}%"
                conditions.append("student_id LIKE ?")
                params.append(clean_q)

            # Outcome filter
            if outcome_filter == "Passed":
                conditions.append("passed = 1")
            elif outcome_filter == "Failed":
                conditions.append("passed = 0")
            elif outcome_filter == "Pending / Unrecorded":
                conditions.append("passed IS NULL")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Count total matches
        count_sql = f"SELECT COUNT(*) FROM students {where_clause};"
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]

        # Fetch records
        select_sql = f"""
        SELECT student_id, attendance_rate, study_hours_per_week, previous_scores,
               assignment_completion_rate, tutoring_sessions, sleep_hours,
               extracurricular, internet_access, final_exam_score, passed, updated_at
        FROM students
        {where_clause}
        ORDER BY student_id ASC
        LIMIT ? OFFSET ?;
        """
        cursor.execute(select_sql, params + [limit, offset])
        records = [dict(row) for row in cursor.fetchall()]

        return records, total_count
    finally:
        if close_conn:
            conn.close()


def add_student(data: dict, requesting_user: dict | None = None, conn = None) -> tuple[bool, str, dict | None]:
    """Adds a new student record after validation and authorization."""
    if requesting_user and not can_manage_students(requesting_user):
        return False, "Permission denied: Only Admin or Faculty can add student records.", None

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        ok, msg = validate_student_record(data, is_new=True, conn=conn)
        if not ok:
            return False, msg, None

        student_id = str(data["student_id"]).strip().upper()
        attendance = float(data["attendance_rate"]) if data.get("attendance_rate") is not None else None
        study_hours = float(data["study_hours_per_week"]) if data.get("study_hours_per_week") is not None else None
        prev_scores = float(data["previous_scores"]) if data.get("previous_scores") is not None else None
        assignments = float(data["assignment_completion_rate"]) if data.get("assignment_completion_rate") is not None else None
        tutoring = int(float(data["tutoring_sessions"])) if data.get("tutoring_sessions") is not None else None
        sleep = float(data["sleep_hours"]) if data.get("sleep_hours") is not None else None
        extra = int(data["extracurricular"])
        internet = int(data["internet_access"])

        final_exam_val = data.get("final_exam_score")
        final_exam = float(final_exam_val) if (final_exam_val is not None and final_exam_val != "") else None

        passed_val = data.get("passed")
        passed = int(passed_val) if (passed_val is not None and passed_val != "") else None

        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO students (
            student_id, attendance_rate, study_hours_per_week, previous_scores,
            assignment_completion_rate, tutoring_sessions, sleep_hours,
            extracurricular, internet_access, final_exam_score, passed,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            student_id, attendance, study_hours, prev_scores,
            assignments, tutoring, sleep, extra, internet,
            final_exam, passed, now, now
        ))
        conn.commit()

        created_student = get_student_by_id(student_id, conn=conn)
        return True, f"Student {student_id} added successfully.", created_student
    except Exception as e:
        return False, f"Failed to add student record: {e}", None
    finally:
        if close_conn:
            conn.close()


def update_student(student_id: str, data: dict, requesting_user: dict | None = None, conn = None) -> tuple[bool, str, dict | None]:
    """Updates an existing student record."""
    if requesting_user and not can_manage_students(requesting_user):
        return False, "Permission denied: Only Admin or Faculty can edit student records.", None

    clean_id = student_id.strip().upper()
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM students WHERE student_id = ?;", (clean_id,))
        if not cursor.fetchone():
            return False, f"Student '{clean_id}' does not exist.", None

        # Validate with existing ID
        data_to_validate = dict(data)
        data_to_validate["student_id"] = clean_id
        ok, msg = validate_student_record(data_to_validate, is_new=False, conn=conn)
        if not ok:
            return False, msg, None

        attendance = float(data["attendance_rate"]) if data.get("attendance_rate") is not None else None
        study_hours = float(data["study_hours_per_week"]) if data.get("study_hours_per_week") is not None else None
        prev_scores = float(data["previous_scores"]) if data.get("previous_scores") is not None else None
        assignments = float(data["assignment_completion_rate"]) if data.get("assignment_completion_rate") is not None else None
        tutoring = int(float(data["tutoring_sessions"])) if data.get("tutoring_sessions") is not None else None
        sleep = float(data["sleep_hours"]) if data.get("sleep_hours") is not None else None
        extra = int(data["extracurricular"])
        internet = int(data["internet_access"])

        final_exam_val = data.get("final_exam_score")
        final_exam = float(final_exam_val) if (final_exam_val is not None and final_exam_val != "") else None

        passed_val = data.get("passed")
        passed = int(passed_val) if (passed_val is not None and passed_val != "") else None

        now = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
        UPDATE students SET
            attendance_rate = ?,
            study_hours_per_week = ?,
            previous_scores = ?,
            assignment_completion_rate = ?,
            tutoring_sessions = ?,
            sleep_hours = ?,
            extracurricular = ?,
            internet_access = ?,
            final_exam_score = ?,
            passed = ?,
            updated_at = ?
        WHERE student_id = ?;
        """, (
            attendance, study_hours, prev_scores,
            assignments, tutoring, sleep, extra, internet,
            final_exam, passed, now, clean_id
        ))
        conn.commit()

        updated_student = get_student_by_id(clean_id, conn=conn)
        return True, f"Student {clean_id} updated successfully.", updated_student
    except Exception as e:
        return False, f"Failed to update student record: {e}", None
    finally:
        if close_conn:
            conn.close()


def delete_student(student_id: str, requesting_user: dict | None = None, conn = None) -> tuple[bool, str]:
    """Deletes a student record. Requires Administrator permission."""
    if requesting_user and not can_delete_student(requesting_user):
        return False, "Permission denied: Only an Administrator can delete student records."

    clean_id = student_id.strip().upper()
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM students WHERE student_id = ?;", (clean_id,))
        if not cursor.fetchone():
            return False, f"Student '{clean_id}' does not exist."

        cursor.execute("DELETE FROM students WHERE student_id = ?;", (clean_id,))
        conn.commit()
        return True, f"Student {clean_id} was deleted successfully."
    except Exception as e:
        return False, f"Failed to delete student record: {e}"
    finally:
        if close_conn:
            conn.close()


def export_students_to_csv(search_query: str = "", outcome_filter: str = "All", requesting_user: dict | None = None, conn = None) -> str:
    """Exports filtered student records to a CSV formatted string."""
    records, _ = list_students(search_query=search_query, outcome_filter=outcome_filter, requesting_user=requesting_user, limit=10000, offset=0, conn=conn)
    if not records:
        return ""

    df = pd.DataFrame(records)
    # Exclude internal timestamp if desired, or keep as export
    return df.to_csv(index=False)


def get_dashboard_summary_metrics(conn = None) -> dict:
    """
    Computes key performance indicators from the database.
    Separates historical actual results from predictions.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()

        # Total counts
        cursor.execute("SELECT COUNT(*) FROM students;")
        total_students = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM students WHERE passed = 1;")
        passed_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM students WHERE passed = 0;")
        failed_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM students WHERE passed IS NULL;")
        unrecorded_count = cursor.fetchone()[0]

        # Averages
        cursor.execute("""
        SELECT
            AVG(attendance_rate) as avg_attendance,
            AVG(study_hours_per_week) as avg_study,
            AVG(previous_scores) as avg_prev_score,
            AVG(assignment_completion_rate) as avg_assignment
        FROM students;
        """)
        row_avg = cursor.fetchone()

        avg_attendance = round(row_avg["avg_attendance"], 1) if row_avg["avg_attendance"] is not None else None
        avg_study = round(row_avg["avg_study"], 1) if row_avg["avg_study"] is not None else None
        avg_prev_score = round(row_avg["avg_prev_score"], 1) if row_avg["avg_prev_score"] is not None else None
        avg_assignment = round(row_avg["avg_assignment"], 1) if row_avg["avg_assignment"] is not None else None

        # Students requiring academic support: Attendance < 75% OR Failed
        cursor.execute("""
        SELECT COUNT(DISTINCT student_id) FROM students
        WHERE (attendance_rate IS NOT NULL AND attendance_rate < 75.0) OR passed = 0;
        """)
        support_needed_count = cursor.fetchone()[0]

        pass_rate = round((passed_count / (passed_count + failed_count) * 100), 1) if (passed_count + failed_count) > 0 else None

        return {
            "total_students": total_students,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "unrecorded_count": unrecorded_count,
            "pass_rate": pass_rate,
            "avg_attendance": avg_attendance,
            "avg_study_hours": avg_study,
            "avg_previous_score": avg_prev_score,
            "avg_assignment_completion": avg_assignment,
            "support_needed_count": support_needed_count
        }
    finally:
        if close_conn:
            conn.close()
