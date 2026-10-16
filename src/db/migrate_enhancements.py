"""
Database migration script for enhancements:
- Creates 'interventions' table (status, follow-up date, author)
- Creates 'audit_logs' table (append-only system trace)
- Adds 'top_factors_json' to 'prediction_history' if not exists
- Adds 'last_login' to 'users' if not exists

Idempotent: Safe to run multiple times without data loss.
"""

import sqlite3
import os
import logging
from src.db.connection import get_db_connection
from src.db.schema import create_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
    return cursor.fetchone() is not None


def run_enhancements_migration(conn=None):
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    cursor = conn.cursor()

    try:
        # 0. Ensure base schema exists before applying any migrations
        create_schema(conn)

        # 1. Create interventions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'In progress', 'Resolved')),
            follow_up_date TEXT,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interventions_student_id ON interventions(student_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interventions_status ON interventions(status);")

        # 2. Create audit_logs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);")

        # 3. Add top_factors_json to prediction_history if missing and table exists
        if _table_exists(cursor, "prediction_history"):
            cursor.execute("PRAGMA table_info(prediction_history);")
            pred_cols = [col[1] for col in cursor.fetchall()]
            if "top_factors_json" not in pred_cols:
                cursor.execute("ALTER TABLE prediction_history ADD COLUMN top_factors_json TEXT;")
                logger.info("Added column top_factors_json to prediction_history")

        # 4. Add last_login to users if missing and table exists
        if _table_exists(cursor, "users"):
            cursor.execute("PRAGMA table_info(users);")
            user_cols = [col[1] for col in cursor.fetchall()]
            if "last_login" not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP;")
                logger.info("Added column last_login to users")

        conn.commit()
        logger.info("Enhancements migration completed successfully.")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration error: {e}")
        raise
    finally:
        if close_at_end:
            conn.close()


if __name__ == "__main__":
    run_enhancements_migration()
