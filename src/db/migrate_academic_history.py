"""
Database migration script to safely create the Four-Year Academic History tables:
- academic_year_records
- semester_results
- subject_results
- student_activities

Preserves all existing student records, user accounts, and prediction history.
"""

import sys
import logging
from src.db.connection import get_db_connection
from src.db.schema import create_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_four_year_history(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        logger.info("Applying Four-Year Academic History schema...")
        create_schema(conn)

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM students;")
        student_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]

        summary = {
            "tables": tables,
            "students_preserved": student_count,
            "users_preserved": user_count,
            "status": "Schema migration successful"
        }
        return summary
    finally:
        if close_conn:
            conn.close()


if __name__ == "__main__":
    result = migrate_four_year_history()
    print("Migration Summary:")
    print(f"  Status: {result['status']}")
    print(f"  Total Tables in DB: {len(result['tables'])}")
    print(f"  Tables: {', '.join(result['tables'])}")
    print(f"  Students Preserved: {result['students_preserved']}")
    print(f"  Users Preserved: {result['users_preserved']}")
