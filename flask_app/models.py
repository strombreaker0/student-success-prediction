"""
Flask-Login User Model and SQLite database wrappers.
Wraps the existing 'users' SQLite table for role-based session management.
"""

from flask_login import UserMixin, AnonymousUserMixin
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

    def is_demo_admin(self) -> bool:
        """Identifies if active user is the Demo Admin persona."""
        import os
        adm = os.environ.get("DEMO_ADMIN_USERNAME", "demo_admin").strip().lower()
        return self.username.strip().lower() == adm

    def is_demo_student(self) -> bool:
        """Identifies if active user is the Demo Student persona."""
        import os
        stu = os.environ.get("DEMO_STUDENT_USERNAME", "demo_student").strip().lower()
        return self.username.strip().lower() == stu

    def can_view_student(self, student_id: str) -> bool:
        """
        Prevents IDOR and protects real data:
        - Students can only view their own linked student profile.
        - Demo Admin can only view synthetic demo student records (STU_DEMO*), never real cohort data.
        - Regular Admins and Faculty can view any student profile.
        """
        clean_id = str(student_id).strip().upper()
        if self.is_demo_admin():
            return clean_id.startswith("STU_DEMO")
        if self.is_admin() or self.role == "faculty":
            return True
        if self.is_student():
            if not self.linked_student_id:
                return False
            return str(self.linked_student_id).strip().upper() == clean_id
        return False

    def can_modify_student(self, student_id: str) -> bool:
        """Demo Admin cannot modify real production student records."""
        clean_id = str(student_id).strip().upper()
        if self.is_demo_admin():
            return clean_id.startswith("STU_DEMO")
        return self.role in ("admin", "faculty")

    def can_delete_student_record(self, student_id: str) -> bool:
        """Demo Admin cannot delete real production student records."""
        clean_id = str(student_id).strip().upper()
        if self.is_demo_admin():
            return clean_id.startswith("STU_DEMO")
        return self.is_admin()

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
            "last_login": self.last_login,
            "is_demo_admin": self.is_demo_admin(),
            "is_demo_student": self.is_demo_student()
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


class AnonymousUser(AnonymousUserMixin):
    """
    Custom anonymous user providing safe defaults for templates and role checks.
    """
    id = None
    username = "visitor"
    email = ""
    role = "visitor"
    full_name = "Presentation Guest"
    linked_student_id = None

    def is_admin(self) -> bool:
        return False

    def is_faculty(self) -> bool:
        return False

    def is_student(self) -> bool:
        return False

    def is_demo_admin(self) -> bool:
        return False

    def is_demo_student(self) -> bool:
        return False

    def can_view_student(self, student_id: str) -> bool:
        return False

    def can_modify_student(self, student_id: str) -> bool:
        return False

    def can_delete_student_record(self, student_id: str) -> bool:
        return False

    def can_manage_students(self) -> bool:
        return False

    def can_delete_students(self) -> bool:
        return False

    def can_manage_users(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {
            "id": None,
            "username": "visitor",
            "email": "",
            "role": "visitor",
            "full_name": "Presentation Guest",
            "linked_student_id": None,
            "is_active": 0,
            "last_login": None,
            "is_demo_admin": False,
            "is_demo_student": False
        }


class DemoAdminPersona:
    """
    Read-only presentation persona representing the Institutional Demo Administrator.
    Used for safe public presentation mode without bypassing authentic admin accounts.
    """
    id = 0
    username = "demo_admin"
    email = "demo.admin@institution.edu"
    role = "admin"
    full_name = "Institutional Demo Administrator"
    linked_student_id = None
    is_active = True
    is_authenticated = False
    is_anonymous = True

    def is_admin(self) -> bool:
        return True

    def is_faculty(self) -> bool:
        return True

    def is_student(self) -> bool:
        return False

    def is_demo_admin(self) -> bool:
        return True

    def is_demo_student(self) -> bool:
        return False

    def can_view_student(self, student_id: str) -> bool:
        return str(student_id).strip().upper().startswith("STU_DEMO")

    def can_modify_student(self, student_id: str) -> bool:
        return False  # Strictly read-only in public presentation mode

    def can_delete_student_record(self, student_id: str) -> bool:
        return False  # Strictly read-only in public presentation mode

    def can_manage_students(self) -> bool:
        return True

    def can_delete_students(self) -> bool:
        return False

    def can_manage_users(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {
            "id": 0,
            "username": "demo_admin",
            "email": "demo.admin@institution.edu",
            "role": "admin",
            "full_name": "Institutional Demo Administrator",
            "linked_student_id": None,
            "is_active": 1,
            "last_login": None,
            "is_demo_admin": True,
            "is_demo_student": False
        }
