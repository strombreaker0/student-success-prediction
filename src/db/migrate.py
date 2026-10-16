"""
Data migration utility.
Safely imports records from data/student_data.csv into SQLite without data loss or duplication.
Handles missing/empty fields as NULL.
"""

import os
import csv
import logging
from src.db.connection import get_db_connection
from src.db.schema import create_schema

logger = logging.getLogger(__name__)


def _parse_float(val):
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "null", "none"):
        return None
    try:
        return float(val_str)
    except ValueError:
        return None


def _parse_int(val):
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "null", "none"):
        return None
    try:
        return int(float(val_str))
    except ValueError:
        return None


def migrate_csv_to_sqlite(csv_path=None, conn=None):
    """
    Reads the CSV and inserts rows into the students table using INSERT OR IGNORE.
    Does not modify or delete the source CSV file.
    Returns a dict with summary statistics.
    """
    if csv_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(base_dir, "data", "student_data.csv")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source student CSV not found at: {csv_path}")

    close_conn_when_done = False
    if conn is None:
        conn = get_db_connection()
        close_conn_when_done = True

    create_schema(conn)

    inserted_count = 0
    skipped_count = 0
    error_count = 0
    total_csv_rows = 0

    cursor = conn.cursor()

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_csv_rows += 1
            student_id = row.get("student_id", "").strip()
            if not student_id:
                skipped_count += 1
                continue

            try:
                attendance_rate = _parse_float(row.get("attendance_rate"))
                study_hours = _parse_float(row.get("study_hours_per_week"))
                previous_scores = _parse_float(row.get("previous_scores"))
                assignment_rate = _parse_float(row.get("assignment_completion_rate"))
                tutoring = _parse_int(row.get("tutoring_sessions"))
                sleep_hours = _parse_float(row.get("sleep_hours"))
                extracurricular = _parse_int(row.get("extracurricular"))
                internet_access = _parse_int(row.get("internet_access"))
                final_exam = _parse_float(row.get("final_exam_score"))
                passed = _parse_int(row.get("passed"))

                cursor.execute("""
                INSERT OR IGNORE INTO students (
                    student_id, attendance_rate, study_hours_per_week,
                    previous_scores, assignment_completion_rate, tutoring_sessions,
                    sleep_hours, extracurricular, internet_access,
                    final_exam_score, passed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    student_id, attendance_rate, study_hours,
                    previous_scores, assignment_rate, tutoring,
                    sleep_hours, extracurricular, internet_access,
                    final_exam, passed
                ))

                if cursor.rowcount > 0:
                    inserted_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                logger.warning(f"Error processing row {student_id}: {e}")
                error_count += 1

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM students;")
    total_in_db = cursor.fetchone()[0]

    if close_conn_when_done:
        conn.close()

    return {
        "total_csv_rows": total_csv_rows,
        "inserted": inserted_count,
        "skipped": skipped_count,
        "errors": error_count,
        "total_in_db": total_in_db
    }


if __name__ == "__main__":
    result = migrate_csv_to_sqlite()
    print("Migration finished:")
    for k, v in result.items():
        print(f"  {k}: {v}")
