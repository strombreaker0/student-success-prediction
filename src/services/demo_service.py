"""
Demo Account & Synthetic Student Provisioning Service.
Idempotently provisions secure demo accounts for Admin and Student personas.
Creates a dedicated synthetic demo student record without modifying or overwriting existing student data.
"""

import os
import logging
from src.db.connection import get_db_connection
from src.services.auth_service import hash_password, register_user
from src.services.student_service import add_student

logger = logging.getLogger(__name__)

# Configurable Demo Personas
DEMO_ADMIN_USERNAME = os.environ.get("DEMO_ADMIN_USERNAME", "demo_admin").strip()
DEMO_ADMIN_EMAIL = os.environ.get("DEMO_ADMIN_EMAIL", "demo.admin@institution.edu").strip()
DEMO_ADMIN_PASSWORD_DEFAULT = os.environ.get("DEMO_ADMIN_PASSWORD", "DemoAdmin#2026!").strip()
DEMO_ADMIN_NAME = os.environ.get("DEMO_ADMIN_NAME", "Institutional Demo Administrator").strip()

DEMO_STUDENT_USERNAME = os.environ.get("DEMO_STUDENT_USERNAME", "demo_student").strip()
DEMO_STUDENT_EMAIL = os.environ.get("DEMO_STUDENT_EMAIL", "demo.student@institution.edu").strip()
DEMO_STUDENT_PASSWORD_DEFAULT = os.environ.get("DEMO_STUDENT_PASSWORD", "DemoStudent#2026!").strip()
DEMO_STUDENT_NAME = os.environ.get("DEMO_STUDENT_NAME", "Demo Student Profile").strip()
DEMO_STUDENT_ID = os.environ.get("DEMO_STUDENT_ID", "STU_DEMO01").strip().upper()


SYNTHETIC_DEMO_STUDENTS = [
    {
        "student_id": "STU_DEMO01",
        "attendance_rate": 88.5,
        "study_hours_per_week": 16.0,
        "previous_scores": 78.0,
        "assignment_completion_rate": 86.0,
        "tutoring_sessions": 2,
        "sleep_hours": 7.0,
        "extracurricular": 1,
        "internet_access": 1,
        "passed": 1,
        "final_exam_score": 76.0
    },
    {
        "student_id": "STU_DEMO02",
        "attendance_rate": 54.0,
        "study_hours_per_week": 6.5,
        "previous_scores": 45.0,
        "assignment_completion_rate": 58.0,
        "tutoring_sessions": 0,
        "sleep_hours": 5.0,
        "extracurricular": 0,
        "internet_access": 1,
        "passed": 0,
        "final_exam_score": 38.0
    },
    {
        "student_id": "STU_DEMO03",
        "attendance_rate": 72.0,
        "study_hours_per_week": 12.0,
        "previous_scores": 66.0,
        "assignment_completion_rate": 74.0,
        "tutoring_sessions": 1,
        "sleep_hours": 6.5,
        "extracurricular": 1,
        "internet_access": 1,
        "passed": 1,
        "final_exam_score": 68.0
    },
    {
        "student_id": "STU_DEMO04",
        "attendance_rate": 96.0,
        "study_hours_per_week": 22.0,
        "previous_scores": 89.0,
        "assignment_completion_rate": 96.0,
        "tutoring_sessions": 3,
        "sleep_hours": 8.0,
        "extracurricular": 1,
        "internet_access": 1,
        "passed": 1,
        "final_exam_score": 91.0
    },
    {
        "student_id": "STU_DEMO05",
        "attendance_rate": 48.0,
        "study_hours_per_week": 5.0,
        "previous_scores": 40.0,
        "assignment_completion_rate": 50.0,
        "tutoring_sessions": 0,
        "sleep_hours": 5.5,
        "extracurricular": 0,
        "internet_access": 0,
        "passed": 0,
        "final_exam_score": 35.0
    }
]


def ensure_demo_student_record(conn=None) -> str:
    """
    Idempotently creates a synthetic demo student cohort and academic trajectory.
    Never modifies existing real student records.
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        cursor = conn.cursor()

        # Seed synthetic demo cohort
        for s in SYNTHETIC_DEMO_STUDENTS:
            cursor.execute("SELECT student_id FROM students WHERE student_id = ?;", (s["student_id"],))
            if not cursor.fetchone():
                add_student(s, requesting_user={"role": "admin", "username": "system"}, conn=conn)
                logger.info(f"Synthetic demo student record '{s['student_id']}' created successfully.")

        # Ensure academic year records for student portal display
        cursor.execute("SELECT id FROM academic_year_records WHERE student_id = ?;", (DEMO_STUDENT_ID,))
        if not cursor.fetchall():
            cursor.execute("""
            INSERT OR IGNORE INTO academic_year_records 
                (student_id, academic_year, year_name, academic_session, status, cgpa, attendance_rate, total_credits_earned, remarks)
            VALUES 
                (?, 1, 'First Year (FYBSc)', '2024-2025', 'Completed', 7.85, 90.0, 40.0, 'Strong foundation in core computing'),
                (?, 2, 'Second Year (SYBSc)', '2025-2026', 'In Progress', 8.10, 88.5, 20.0, 'Consistent coursework engagement');
            """, (DEMO_STUDENT_ID, DEMO_STUDENT_ID))

        # Ensure a baseline prediction history entry exists for demo student
        cursor.execute("SELECT id FROM prediction_history WHERE student_id = ?;", (DEMO_STUDENT_ID,))
        if not cursor.fetchone():
            try:
                from src.services.prediction_service import predict_student
                student_features = {
                    "student_id": DEMO_STUDENT_ID,
                    "attendance_rate": 88.5,
                    "study_hours_per_week": 16.0,
                    "previous_scores": 78.0,
                    "assignment_completion_rate": 86.0,
                    "tutoring_sessions": 2,
                    "sleep_hours": 7.0,
                    "extracurricular": 1,
                    "internet_access": 1
                }
                predict_student(
                    student_features,
                    model_name="Random Forest",
                    actor_username="system",
                    save_history=True,
                    conn=conn
                )
            except Exception as ml_err:
                logger.warning(f"Note: Could not generate initial demo prediction: {ml_err}")

        conn.commit()
        return DEMO_STUDENT_ID
    finally:
        if close_at_end:
            conn.close()


def provision_demo_accounts(admin_password=None, student_password=None, conn=None) -> dict:
    """
    Explicit, repeatable routine to provision or update the two demo accounts.
    Idempotent: Safe to execute repeatedly without resetting the database or modifying existing records.
    Do not log passwords.
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    adm_pass = admin_password or DEMO_ADMIN_PASSWORD_DEFAULT
    stu_pass = student_password or DEMO_STUDENT_PASSWORD_DEFAULT

    results = {
        "status": "success",
        "admin": None,
        "student": None
    }

    try:
        # Step 1: Ensure dedicated demo student profile exists
        sid = ensure_demo_student_record(conn)

        cursor = conn.cursor()

        # Step 2: Provision / Synchronize Admin Demo Account
        cursor.execute("SELECT id, username, email, role FROM users WHERE username = ? COLLATE NOCASE;", (DEMO_ADMIN_USERNAME,))
        existing_admin = cursor.fetchone()

        if existing_admin:
            # Update password hash and guarantee admin role & active status
            new_hash = hash_password(adm_pass)
            cursor.execute("""
            UPDATE users 
            SET password_hash = ?, role = 'admin', is_active = 1, full_name = ?
            WHERE id = ?;
            """, (new_hash, DEMO_ADMIN_NAME, existing_admin["id"]))
            results["admin"] = {
                "username": DEMO_ADMIN_USERNAME,
                "email": existing_admin["email"],
                "role": "admin",
                "action": "updated"
            }
            logger.info(f"Demo admin account '{DEMO_ADMIN_USERNAME}' synchronized successfully.")
        else:
            ok, msg, created = register_user(
                username=DEMO_ADMIN_USERNAME,
                email=DEMO_ADMIN_EMAIL,
                password=adm_pass,
                role="admin",
                full_name=DEMO_ADMIN_NAME,
                conn=conn
            )
            if ok:
                results["admin"] = {
                    "username": DEMO_ADMIN_USERNAME,
                    "email": DEMO_ADMIN_EMAIL,
                    "role": "admin",
                    "action": "created"
                }
                logger.info(f"Demo admin account '{DEMO_ADMIN_USERNAME}' created successfully.")
            else:
                logger.error(f"Failed to create demo admin: {msg}")
                results["admin"] = {"error": msg}

        # Step 3: Provision / Synchronize Student Demo Account
        cursor.execute("SELECT id, username, email, role, linked_student_id FROM users WHERE username = ? COLLATE NOCASE;", (DEMO_STUDENT_USERNAME,))
        existing_student = cursor.fetchone()

        if existing_student:
            new_hash = hash_password(stu_pass)
            cursor.execute("""
            UPDATE users 
            SET password_hash = ?, role = 'student', is_active = 1, linked_student_id = ?, full_name = ?
            WHERE id = ?;
            """, (new_hash, sid, DEMO_STUDENT_NAME, existing_student["id"]))
            results["student"] = {
                "username": DEMO_STUDENT_USERNAME,
                "email": existing_student["email"],
                "role": "student",
                "linked_student_id": sid,
                "action": "updated"
            }
            logger.info(f"Demo student account '{DEMO_STUDENT_USERNAME}' synchronized successfully.")
        else:
            ok, msg, created = register_user(
                username=DEMO_STUDENT_USERNAME,
                email=DEMO_STUDENT_EMAIL,
                password=stu_pass,
                role="student",
                full_name=DEMO_STUDENT_NAME,
                linked_student_id=sid,
                conn=conn
            )
            if ok:
                results["student"] = {
                    "username": DEMO_STUDENT_USERNAME,
                    "email": DEMO_STUDENT_EMAIL,
                    "role": "student",
                    "linked_student_id": sid,
                    "action": "created"
                }
                logger.info(f"Demo student account '{DEMO_STUDENT_USERNAME}' created successfully.")
            else:
                logger.error(f"Failed to create demo student: {msg}")
                results["student"] = {"error": msg}

        conn.commit()
        return results
    except Exception as e:
        conn.rollback()
        logger.error(f"Error provisioning demo accounts: {e}")
        raise
    finally:
        if close_at_end:
            conn.close()


def get_demo_account_status(conn=None) -> dict:
    """Returns readiness status for demo accounts without exposing sensitive fields."""
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, role, is_active FROM users WHERE username = ? COLLATE NOCASE;", (DEMO_ADMIN_USERNAME,))
        admin_row = cursor.fetchone()

        cursor.execute("SELECT id, role, is_active, linked_student_id FROM users WHERE username = ? COLLATE NOCASE;", (DEMO_STUDENT_USERNAME,))
        student_row = cursor.fetchone()

        return {
            "admin_ready": bool(admin_row and admin_row["is_active"] and admin_row["role"] == "admin"),
            "student_ready": bool(student_row and student_row["is_active"] and student_row["role"] == "student" and student_row["linked_student_id"]),
            "admin_username": DEMO_ADMIN_USERNAME,
            "student_username": DEMO_STUDENT_USERNAME,
            "demo_student_id": DEMO_STUDENT_ID
        }
    finally:
        if close_at_end:
            conn.close()
