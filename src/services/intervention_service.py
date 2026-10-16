"""
Intervention Management Service.
Handles student remedial interventions, tracking statuses (Open, In progress, Resolved),
target follow-up dates, notes, and role-based access control.
"""

import sqlite3
import logging
from datetime import datetime, timezone, date
from src.db.connection import get_db_connection
from src.services.auth_service import can_view_student

logger = logging.getLogger(__name__)

VALID_STATUSES = ("Open", "In progress", "Resolved")


def create_intervention(
    student_id: str,
    title: str,
    description: str = "",
    follow_up_date: str = None,
    created_by: str = "system",
    requesting_user: dict = None,
    conn = None
) -> tuple[bool, str, dict]:
    """
    Creates a new intervention record for a student.
    Enforces that requesting_user (if provided) has permission to manage student.
    """
    if requesting_user:
        role = requesting_user.get("role")
        if role == "student":
            return False, "Students cannot create academic interventions.", {}

    if not student_id or not title:
        return False, "Student ID and Intervention Title are required.", {}

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        # Verify student exists
        cursor.execute("SELECT student_id FROM students WHERE student_id = ?;", (str(student_id).strip().upper(),))
        if not cursor.fetchone():
            return False, f"Student '{student_id}' does not exist.", {}

        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        INSERT INTO interventions (
            student_id, title, description, status, follow_up_date, created_by, created_at, updated_at
        ) VALUES (?, ?, ?, 'Open', ?, ?, ?, ?);
        """, (
            str(student_id).strip().upper(),
            title.strip(),
            (description or "").strip(),
            follow_up_date.strip() if follow_up_date else None,
            created_by,
            now_str,
            now_str
        ))
        conn.commit()
        new_id = cursor.lastrowid

        return True, "Intervention recorded successfully.", {
            "id": new_id,
            "student_id": str(student_id).strip().upper(),
            "title": title.strip(),
            "description": description or "",
            "status": "Open",
            "follow_up_date": follow_up_date,
            "created_by": created_by,
            "created_at": now_str,
            "updated_at": now_str
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating intervention: {e}")
        return False, f"Database error creating intervention: {str(e)}", {}
    finally:
        if close_conn:
            conn.close()


def update_intervention(
    intervention_id: int,
    status: str = None,
    follow_up_date: str = None,
    description: str = None,
    title: str = None,
    requesting_user: dict = None,
    conn = None
) -> tuple[bool, str, dict]:
    """
    Updates an intervention's status, follow-up date, or details.
    """
    if requesting_user:
        role = requesting_user.get("role")
        if role == "student":
            return False, "Students cannot modify interventions.", {}

    if status and status not in VALID_STATUSES:
        return False, f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}", {}

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM interventions WHERE id = ?;", (intervention_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Intervention #{intervention_id} not found.", {}

        # If faculty, ensure they can view this student
        if requesting_user and requesting_user.get("role") == "faculty":
            if not can_view_student(requesting_user, row["student_id"]):
                return False, "Access denied: you do not have permission to edit this student's intervention.", {}

        new_status = status if status else row["status"]
        new_date = follow_up_date if follow_up_date is not None else row["follow_up_date"]
        new_desc = description if description is not None else row["description"]
        new_title = title if title is not None else row["title"]
        now_str = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
        UPDATE interventions
        SET status = ?, follow_up_date = ?, description = ?, title = ?, updated_at = ?
        WHERE id = ?;
        """, (new_status, new_date, new_desc, new_title, now_str, intervention_id))
        conn.commit()

        return True, "Intervention updated successfully.", {
            "id": intervention_id,
            "student_id": row["student_id"],
            "title": new_title,
            "status": new_status,
            "follow_up_date": new_date,
            "description": new_desc,
            "updated_at": now_str
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating intervention: {e}")
        return False, f"Database error: {str(e)}", {}
    finally:
        if close_conn:
            conn.close()


def list_interventions(
    student_id: str = None,
    status: str = None,
    search: str = None,
    requesting_user: dict = None,
    limit: int = 100,
    offset: int = 0,
    conn = None
) -> tuple[list[dict], int]:
    """
    Fetches list of interventions with optional status, student_id, and search filters.
    Respects student privacy: a student user can ONLY see interventions for their linked student ID.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        where_clauses = []
        params = []

        # Role enforcement
        is_demo_admin = requesting_user and (requesting_user.get("is_demo_admin") or str(requesting_user.get("username", "")).strip().lower() == "demo_admin")
        if requesting_user and requesting_user.get("role") == "student":
            linked_id = requesting_user.get("linked_student_id")
            if not linked_id:
                return [], 0
            where_clauses.append("student_id = ?")
            params.append(linked_id)
        elif is_demo_admin:
            if student_id:
                if not str(student_id).strip().upper().startswith("STU_DEMO"):
                    return [], 0
                where_clauses.append("student_id = ?")
                params.append(str(student_id).strip().upper())
            else:
                where_clauses.append("student_id LIKE 'STU_DEMO%'")
        elif student_id:
            where_clauses.append("student_id = ?")
            params.append(str(student_id).strip().upper())

        if status and status in VALID_STATUSES:
            where_clauses.append("status = ?")
            params.append(status)

        if search:
            where_clauses.append("(title LIKE ? OR description LIKE ? OR student_id LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend([term, term, term])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Total count
        count_query = f"SELECT COUNT(*) FROM interventions {where_sql};"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # Fetch page
        query = f"""
        SELECT id, student_id, title, description, status, follow_up_date, created_by, created_at, updated_at
        FROM interventions
        {where_sql}
        ORDER BY 
            CASE status 
                WHEN 'Open' THEN 1 
                WHEN 'In progress' THEN 2 
                ELSE 3 
            END ASC,
            follow_up_date ASC,
            created_at DESC
        LIMIT ? OFFSET ?;
        """
        cursor.execute(query, params + [limit, offset])
        rows = [dict(r) for r in cursor.fetchall()]
        return rows, total
    finally:
        if close_conn:
            conn.close()


def get_overdue_interventions(requesting_user: dict = None, conn = None) -> list[dict]:
    """
    Returns open or in-progress interventions whose follow_up_date is before today.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        today_str = date.today().isoformat()
        where_clauses = ["status != 'Resolved'", "follow_up_date IS NOT NULL", "follow_up_date < ?"]
        params = [today_str]

        is_demo_admin = requesting_user and (requesting_user.get("is_demo_admin") or str(requesting_user.get("username", "")).strip().lower() == "demo_admin")
        if requesting_user and requesting_user.get("role") == "student":
            linked_id = requesting_user.get("linked_student_id")
            where_clauses.append("student_id = ?")
            params.append(linked_id or "")
        elif is_demo_admin:
            where_clauses.append("student_id LIKE 'STU_DEMO%'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}"
        cursor.execute(f"""
        SELECT id, student_id, title, description, status, follow_up_date, created_by, created_at
        FROM interventions
        {where_sql}
        ORDER BY follow_up_date ASC;
        """, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        if close_conn:
            conn.close()
