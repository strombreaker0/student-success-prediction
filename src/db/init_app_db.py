"""
Application Database Initializer and Bootstrapper.
Ensures tables exist, migrations run safely and incrementally,
and seeds baseline dataset/admin user only when starting with an uninitialized database.
Preserves existing records at all times.
"""

import os
import logging
from src.db.connection import get_db_connection, get_db_path
from src.db.schema import create_schema
from src.db.migrate_enhancements import run_enhancements_migration
from src.db.migrate import migrate_csv_to_sqlite

logger = logging.getLogger(__name__)


def ensure_db_initialized(conn=None, db_path=None, seed_csv_if_empty=True, bootstrap_admin_if_empty=True):
    """
    Idempotent database initialization and bootstrapping routine.
    Safe for both local execution and cloud deployment (e.g. Render).
    
    1. Ensures target database directory exists.
    2. Creates all schema tables and indexes if missing.
    3. Runs safe enhancements migrations.
    4. Auto-seeds baseline students from student_data.csv ONLY if students table is empty and seed_csv_if_empty is True.
    5. Auto-provisions initial administrator from environment variables ONLY if users table is empty and bootstrap_admin_if_empty is True.
    
    Preserves all existing records. Never deletes or truncates data.
    """
    close_at_end = False
    if conn is None:
        target_path = get_db_path(db_path)
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        conn = get_db_connection(target_path)
        close_at_end = True

    try:
        cursor = conn.cursor()

        # Step 1: Ensure base schema and indexes
        create_schema(conn)

        # Step 2: Ensure migrations and enhancements
        run_enhancements_migration(conn)

        # Step 3: Check student records (seed from CSV only if 0 students exist)
        cursor.execute("SELECT COUNT(*) FROM students;")
        student_count = cursor.fetchone()[0]

        if student_count == 0 and seed_csv_if_empty:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            csv_path = os.path.join(base_dir, "data", "student_data.csv")
            if os.path.exists(csv_path):
                logger.info(f"Empty database detected. Seeding baseline students from {csv_path}...")
                seed_res = migrate_csv_to_sqlite(csv_path=csv_path, conn=conn)
                student_count = seed_res.get("total_in_db", seed_res.get("inserted", 0))
                logger.info(f"Seeded {seed_res.get('inserted', 0)} baseline student records.")
            else:
                logger.warning(f"Student CSV not found at {csv_path}. Database left with 0 students.")
        else:
            logger.info(f"Verified {student_count} student records present in database.")

        # Step 4: Check user accounts (bootstrap admin from env only if 0 users exist)
        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]

        if user_count == 0 and bootstrap_admin_if_empty:
            admin_user = os.environ.get("ADMIN_USERNAME", "admin").strip()
            admin_email = os.environ.get("ADMIN_EMAIL", "admin@institution.edu").strip()
            admin_pass = os.environ.get("ADMIN_PASSWORD", "").strip()
            admin_name = os.environ.get("ADMIN_NAME", "System Administrator").strip()

            if admin_pass:
                from src.services.auth_service import register_user
                ok, msg, user = register_user(
                    username=admin_user,
                    email=admin_email,
                    password=admin_pass,
                    role="admin",
                    full_name=admin_name,
                    conn=conn
                )
                if ok:
                    user_count = 1
                    logger.info(f"Auto-provisioned initial admin user '{admin_user}' ({admin_email}) from environment variables.")
                else:
                    logger.warning(f"Failed to auto-provision admin user '{admin_user}': {msg}")
            else:
                logger.info("No user accounts exist in database and ADMIN_PASSWORD is not set. "
                            "Set ADMIN_PASSWORD in environment variables to auto-provision an admin on boot.")
        else:
            logger.info(f"Verified {user_count} user accounts present in database.")

        conn.commit()
        return {
            "status": "ready",
            "students": student_count,
            "users": user_count
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        if close_at_end:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = ensure_db_initialized()
    print("Database initialization result:", res)
