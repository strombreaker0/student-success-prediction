"""
Audit Logging Service.
Records immutable security and operational events (login, logout, student CRUD,
prediction runs, report exports, and role changes) without sensitive credentials.
Provides search, filtering, and pagination exclusively for administrators.
"""

import sqlite3
import logging
from datetime import datetime, timezone
from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

# Sensitive keywords to filter out of any audit log details
SENSITIVE_KEYS = ("password", "passwd", "token", "secret", "hash", "key", "authorization")


def sanitize_details(details: str) -> str:
    """Removes or masks any sensitive credential data before persisting to audit log."""
    if not details:
        return ""
    clean = str(details)
    for kw in SENSITIVE_KEYS:
        if kw in clean.lower():
            # If details contain sensitive field mention, mask suspicious content
            lines = clean.splitlines()
            safe_lines = []
            for line in lines:
                if any(k in line.lower() for k in SENSITIVE_KEYS):
                    safe_lines.append(f"[MASKED_CREDENTIAL_DATA_{kw.upper()}]")
                else:
                    safe_lines.append(line)
            clean = "\n".join(safe_lines)
    return clean


def log_audit_event(
    username: str,
    action: str,
    target: str = None,
    details: str = None,
    user_id: int = None,
    ip_address: str = None,
    conn = None
) -> bool:
    """
    Appends an immutable audit event to the audit_logs table.
    """
    close_conn = False
    if conn is None:
        try:
            conn = get_db_connection()
            close_conn = True
        except Exception as e:
            logger.warning(f"Failed to acquire db connection for audit log: {e}")
            return False

    try:
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).isoformat()
        clean_details = sanitize_details(details) if details else ""

        cursor.execute("""
        INSERT INTO audit_logs (
            user_id, username, action, target, details, ip_address, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            user_id,
            username or "anonymous",
            action,
            target or "",
            clean_details,
            ip_address or "127.0.0.1",
            now_str
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.warning(f"Could not write audit log: {e}")
        return False
    finally:
        if close_conn:
            conn.close()


def list_audit_logs(
    search: str = None,
    action: str = None,
    username: str = None,
    page: int = 1,
    per_page: int = 25,
    requesting_user: dict = None,
    conn = None
) -> tuple[list[dict], int]:
    """
    Lists audit logs with search, action filtering, and pagination.
    Restricted strictly to administrators.
    """
    if requesting_user and requesting_user.get("role") != "admin":
        raise PermissionError("Access denied: only administrators may inspect system audit logs.")

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        where_clauses = []
        params = []

        if action:
            where_clauses.append("action = ?")
            params.append(action)

        if username:
            where_clauses.append("username LIKE ?")
            params.append(f"%{username.strip()}%")

        if search:
            where_clauses.append("(username LIKE ? OR action LIKE ? OR target LIKE ? OR details LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend([term, term, term, term])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cursor.execute(f"SELECT COUNT(*) FROM audit_logs {where_sql};", params)
        total = cursor.fetchone()[0]

        offset = max(0, (page - 1) * per_page)
        query = f"""
        SELECT id, user_id, username, action, target, details, ip_address, created_at
        FROM audit_logs
        {where_sql}
        ORDER BY created_at DESC, id DESC
        LIMIT ? OFFSET ?;
        """
        cursor.execute(query, params + [per_page, offset])
        logs = [dict(r) for r in cursor.fetchall()]
        return logs, total
    finally:
        if close_conn:
            conn.close()
