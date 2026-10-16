"""
Flask-Login User Model and SQLite database wrappers.
Wraps the existing 'users' SQLite table for role-based session management.
"""

from flask_login import UserMixin
from src.db.connection import get_db_connection


class User(UserMixin):
    """
    Authenticated User entity for Flask-Login session management.
    """
    def __init__(self, id, username, email, role, full_name, linked_student_id=None, is_active=1, last_login=None):
        self.id = int(id)
        self.username = username
        self.email = email
        self.role = role
        self.full_name = full_name
        self.linked_student_id = linked_student_id
        self._is_active = bool(is_active)
        self.last_login = last_login

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self._is_active

    def is_admin(self):
        return self.role == "admin"

    def is_faculty(self):
        return self.role in ("faculty", "admin")

    def is_student(self):
        return self.role == "student"

    def can_view_student(self, student_id: str) -> bool:
        """
        Prevents IDOR: Students can only view their own linked student profile.
        Admins and Faculty can view any student profile.
        """
        if self.is_admin() or self.role == "faculty":
            return True
        if self.is_student():
            if not self.linked_student_id:
                return False
            return str(self.linked_student_id).strip().upper() == str(student_id).strip().upper()
        return False

    def can_manage_students(self) -> bool:
        """Only admins and faculty can add/edit student records."""
        return self.role in ("admin", "faculty")

    def can_delete_students(self) -> bool:
        """Only administrators can delete student records."""
        return self.role == "admin"

    def can_manage_users(self) -> bool:
        """Only administrators can manage system users."""
        return self.role == "admin"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
            "linked_student_id": self.linked_student_id,
            "is_active": int(self._is_active),
            "last_login": self.last_login
        }

    @classmethod
    def get_by_id(cls, user_id, conn=None):
        """Fetches a user by numeric primary key."""
        close_conn = False
        if conn is None:
            try:
                conn = get_db_connection()
                close_conn = True
            except Exception:
                return None

        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, username, email, role, full_name, linked_student_id, is_active, last_login
            FROM users WHERE id = ?;
            """, (int(user_id),))
            row = cursor.fetchone()
            if row:
                return cls(
                    id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    role=row["role"],
                    full_name=row["full_name"],
                    linked_student_id=row["linked_student_id"],
                    is_active=row["is_active"],
                    last_login=row["last_login"]
                )
            return None
        except Exception:
            return None
        finally:
            if close_conn:
                conn.close()

    @classmethod
    def get_by_identifier(cls, identifier, conn=None):
        """Fetches a user by username or email."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, username, email, role, full_name, linked_student_id, is_active, last_login
            FROM users 
            WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE;
            """, (str(identifier).strip(), str(identifier).strip()))
            row = cursor.fetchone()
            if row:
                return cls(
                    id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    role=row["role"],
                    full_name=row["full_name"],
                    linked_student_id=row["linked_student_id"],
                    is_active=row["is_active"],
                    last_login=row["last_login"]
                )
            return None
        finally:
            if close_conn:
                conn.close()
