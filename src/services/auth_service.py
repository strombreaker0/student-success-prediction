"""
Authentication and Role-Based Access Control (RBAC) Service.
Handles password hashing, user registration, authentication, sessions, and authorization checks.
"""

import re
import secrets
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from src.db.connection import get_db_connection

VALID_ROLES = ("admin", "faculty", "student")
DEFAULT_SESSION_TIMEOUT_MINUTES = 60


def hash_password(password: str) -> str:
    """Hashes a plaintext password using secure PBKDF2 with SHA-256."""
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def verify_password(stored_hash: str, password: str) -> bool:
    """Verifies a plaintext password against a stored secure hash."""
    if not stored_hash or not password:
        return False
    return check_password_hash(stored_hash, password)


def validate_username(username: str) -> tuple[bool, str]:
    if not username or not isinstance(username, str):
        return False, "Username is required."
    username = username.strip()
    if len(username) < 3 or len(username) > 30:
        return False, "Username must be between 3 and 30 characters."
    if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
        return False, "Username can only contain alphanumeric characters, underscores, dashes, and dots."
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    if not email or not isinstance(email, str):
        return False, "Email address is required."
    email = email.strip()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        return False, "Please enter a valid email address (e.g. user@institution.edu)."
    return True, ""


def validate_password_strength(password: str) -> tuple[bool, str]:
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numeric digit."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    return True, ""


def validate_registration(
    username: str,
    email: str,
    password: str,
    role: str,
    full_name: str,
    linked_student_id: str = None,
    conn=None
) -> tuple[bool, str]:
    """Validates all inputs for user registration against format and database uniqueness."""
    valid_u, msg_u = validate_username(username)
    if not valid_u:
        return False, msg_u

    valid_e, msg_e = validate_email(email)
    if not valid_e:
        return False, msg_e

    valid_p, msg_p = validate_password_strength(password)
    if not valid_p:
        return False, msg_p

    if not full_name or not full_name.strip():
        return False, "Full Name is required."

    if role not in VALID_ROLES:
        return False, f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        # Check username uniqueness
        cursor.execute("SELECT id FROM users WHERE username = ? COLLATE NOCASE;", (username.strip(),))
        if cursor.fetchone():
            return False, f"Username '{username.strip()}' is already taken."

        # Check email uniqueness
        cursor.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE;", (email.strip(),))
        if cursor.fetchone():
            return False, f"An account with email '{email.strip()}' already exists."

        # Check student linkage
        if role == "student":
            if not linked_student_id or not linked_student_id.strip():
                return False, "A Student account must be linked to a valid Student ID."
            sid = linked_student_id.strip()
            cursor.execute("SELECT student_id FROM students WHERE student_id = ?;", (sid,))
            if not cursor.fetchone():
                return False, f"Student ID '{sid}' was not found in the student records database."

            cursor.execute("SELECT id, username FROM users WHERE linked_student_id = ? AND is_active = 1;", (sid,))
            existing_user = cursor.fetchone()
            if existing_user:
                return False, f"Student ID '{sid}' is already linked to active user '{existing_user['username']}'."

        return True, ""
    finally:
        if close_conn:
            conn.close()


def register_user(
    username: str,
    email: str,
    password: str,
    role: str,
    full_name: str,
    linked_student_id: str = None,
    conn=None
) -> tuple[bool, str, dict | None]:
    """Registers a new user after validation and hashes the password."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        is_valid, err_msg = validate_registration(
            username=username,
            email=email,
            password=password,
            role=role,
            full_name=full_name,
            linked_student_id=linked_student_id,
            conn=conn
        )
        if not is_valid:
            return False, err_msg, None

        pwd_hash = hash_password(password)
        cleaned_sid = linked_student_id.strip() if (role == "student" and linked_student_id) else None

        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, role, full_name, linked_student_id, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1);
        """, (
            username.strip(),
            email.strip().lower(),
            pwd_hash,
            role,
            full_name.strip(),
            cleaned_sid
        ))
        conn.commit()
        user_id = cursor.lastrowid

        user_data = {
            "id": user_id,
            "username": username.strip(),
            "email": email.strip().lower(),
            "role": role,
            "full_name": full_name.strip(),
            "linked_student_id": cleaned_sid,
            "is_active": 1
        }
        return True, "Account registered successfully.", user_data
    except Exception as e:
        return False, f"Failed to register account: {e}", None
    finally:
        if close_conn:
            conn.close()


_FAILED_ATTEMPTS = {}  # identifier -> list of timestamps (float)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900  # 15 minutes


def is_rate_limited(identifier: str) -> bool:
    """Checks if an identifier has exceeded allowed failed login attempts."""
    import time
    key = str(identifier).strip().lower()
    now = time.time()
    if key in _FAILED_ATTEMPTS:
        # Keep only attempts within window
        valid_attempts = [t for t in _FAILED_ATTEMPTS[key] if now - t < LOGIN_LOCKOUT_SECONDS]
        _FAILED_ATTEMPTS[key] = valid_attempts
        return len(valid_attempts) >= MAX_LOGIN_ATTEMPTS
    return False


def record_failed_attempt(identifier: str):
    """Records a failed attempt timestamp for brute-force protection."""
    import time
    key = str(identifier).strip().lower()
    now = time.time()
    if key not in _FAILED_ATTEMPTS:
        _FAILED_ATTEMPTS[key] = []
    _FAILED_ATTEMPTS[key].append(now)


def clear_failed_attempts(identifier: str):
    """Clears failed attempts upon successful login."""
    key = str(identifier).strip().lower()
    _FAILED_ATTEMPTS.pop(key, None)


def authenticate_user(username_or_email: str, password: str, conn=None) -> tuple[bool, str, dict | None]:
    """Authenticates a user by username or email and validates password hash."""
    from datetime import datetime, timezone

    if not username_or_email or not password:
        return False, "Please provide both identifier and password.", None

    identifier = username_or_email.strip()

    if is_rate_limited(identifier):
        return False, "Too many failed login attempts. Please try again after 15 minutes.", None

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, username, email, password_hash, role, full_name, linked_student_id, is_active, last_login
        FROM users
        WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE;
        """, (identifier, identifier))
        row = cursor.fetchone()

        if not row:
            record_failed_attempt(identifier)
            return False, "Invalid username/email or password.", None

        if not row["is_active"]:
            return False, "This account has been deactivated. Please contact an administrator.", None

        if not verify_password(row["password_hash"], password):
            record_failed_attempt(identifier)
            return False, "Invalid username/email or password.", None

        # Reset failed attempts on success
        clear_failed_attempts(identifier)

        now_str = datetime.now(timezone.utc).isoformat()
        try:
            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?;", (now_str, row["id"]))
            conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update last_login: {e}")

        user_dict = {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "full_name": row["full_name"],
            "linked_student_id": row["linked_student_id"],
            "is_active": row["is_active"],
            "last_login": row["last_login"] or now_str
        }
        return True, "Authentication successful.", user_dict
    finally:
        if close_conn:
            conn.close()


def has_admin_user(conn=None) -> bool:
    """Checks whether at least one active administrator account exists in the database."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1;")
        count = cursor.fetchone()[0]
        return count > 0
    finally:
        if close_conn:
            conn.close()


def list_users(conn=None) -> list[dict]:
    """Lists all user accounts (excluding password hashes). For admin use."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, username, email, role, full_name, linked_student_id, is_active, created_at
        FROM users
        ORDER BY created_at DESC;
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if close_conn:
            conn.close()


def update_user_status(user_id: int, is_active: int, conn=None) -> tuple[bool, str]:
    """Enables or disables a user account."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?;", (1 if is_active else 0, user_id))
        conn.commit()
        return True, "User status updated successfully."
    except Exception as e:
        return False, f"Failed to update status: {e}"
    finally:
        if close_conn:
            conn.close()


def update_user_role(user_id: int, new_role: str, conn=None) -> tuple[bool, str]:
    """Updates a user's role with validation."""
    if new_role not in VALID_ROLES:
        return False, f"Invalid role: {new_role}"
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?;", (new_role, user_id))
        conn.commit()
        return True, f"User role updated to {new_role}."
    except Exception as e:
        return False, f"Failed to update role: {e}"
    finally:
        if close_conn:
            conn.close()


# ---------------- Session Management ----------------

def create_session(user_dict: dict) -> dict:
    """Creates a secure session object with tracking timestamps."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "user": user_dict,
        "token": secrets.token_hex(24),
        "created_at": now,
        "last_activity": now
    }


def is_session_expired(session_dict: dict, timeout_minutes: int = DEFAULT_SESSION_TIMEOUT_MINUTES) -> bool:
    """Checks whether the session has exceeded the inactivity timeout."""
    if not session_dict or "last_activity" not in session_dict:
        return True
    try:
        last_dt = datetime.fromisoformat(session_dict["last_activity"])
        now_dt = datetime.now(timezone.utc)
        elapsed = (now_dt - last_dt).total_seconds()
        return elapsed > (timeout_minutes * 60)
    except Exception:
        return True


def refresh_session_activity(session_dict: dict) -> None:
    """Updates last activity timestamp for active session."""
    if session_dict:
        session_dict["last_activity"] = datetime.now(timezone.utc).isoformat()


# ---------------- Permission & Authorization Checkers ----------------

def can_view_student(user: dict | None, student_id: str) -> bool:
    """
    Authorizes viewing of student records:
    - Demo Admin: can ONLY view synthetic demo students (STU_DEMO*), never real cohort data.
    - Regular Admin/Faculty: can view any student.
    - Student: can ONLY view their own profile where student_id == linked_student_id.
    """
    if not user:
        return False
    clean_id = str(student_id).strip().upper()
    if user.get("is_demo_admin") or str(user.get("username", "")).strip().lower() == "demo_admin":
        return clean_id.startswith("STU_DEMO")
    role = user.get("role")
    if role in ("admin", "faculty"):
        return True
    if role == "student":
        return str(user.get("linked_student_id", "")).strip().upper() == clean_id
    return False


def can_manage_students(user: dict | None) -> bool:
    """Authorizes adding and editing student records: Admin and Faculty."""
    if not user:
        return False
    return user.get("role") in ("admin", "faculty")


def can_delete_student(user: dict | None, student_id: str | None = None) -> bool:
    """Authorizes student record deletion: Administrator only. Demo admin cannot delete production records."""
    if not user:
        return False
    if user.get("role") != "admin":
        return False
    if student_id and (user.get("is_demo_admin") or str(user.get("username", "")).strip().lower() == "demo_admin"):
        return str(student_id).strip().upper().startswith("STU_DEMO")
    return True


def can_manage_users(user: dict | None) -> bool:
    """Authorizes viewing and managing user accounts: Administrator only."""
    if not user:
        return False
    return user.get("role") == "admin"


def can_run_predictions(user: dict | None) -> bool:
    """Authorizes running ML predictions on students: Admin and Faculty."""
    if not user:
        return False
    return user.get("role") in ("admin", "faculty")
