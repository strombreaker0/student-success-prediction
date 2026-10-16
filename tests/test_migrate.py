"""
Unit and integration tests for data migration from CSV to SQLite.
"""

import os
import tempfile
import pytest
from src.db.connection import get_db_connection
from src.db.migrate import migrate_csv_to_sqlite


@pytest.fixture
def temp_csv_and_db():
    # Temp DB
    fd_db, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd_db)

    # Temp CSV with regular rows, empty values, and duplicated student IDs
    csv_content = """student_id,attendance_rate,study_hours_per_week,previous_scores,assignment_completion_rate,tutoring_sessions,sleep_hours,extracurricular,internet_access,final_exam_score,passed
STU_M1,80.5,15.2,70.0,85.0,2,7.0,1,1,55.0,1
STU_M2,,12.0,60.0,75.0,1,6.5,0,1,45.0,0
STU_M1,90.0,20.0,80.0,90.0,3,8.0,1,1,70.0,1
STU_M3,95.0,,90.0,98.0,4,8.0,1,1,,
"""
    fd_csv, csv_path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd_csv, "w", encoding="utf-8") as f:
        f.write(csv_content)

    yield csv_path, db_path

    if os.path.exists(csv_path):
        os.remove(csv_path)
    if os.path.exists(db_path):
        os.remove(db_path)


def test_migration_pipeline(temp_csv_and_db):
    csv_path, db_path = temp_csv_and_db
    conn = get_db_connection(db_path)

    # First migration run
    res = migrate_csv_to_sqlite(csv_path=csv_path, conn=conn)
    assert res["total_csv_rows"] == 4
    # STU_M1 (first), STU_M2 (missing attendance), STU_M3 (missing study_hours & final score) -> 3 distinct
    # Second STU_M1 is duplicate -> skipped
    assert res["inserted"] == 3
    assert res["skipped"] == 1
    assert res["total_in_db"] == 3

    # Check that STU_M2 has None for attendance_rate and was not rejected
    cursor = conn.cursor()
    cursor.execute("SELECT attendance_rate, study_hours_per_week FROM students WHERE student_id = 'STU_M2';")
    row2 = cursor.fetchone()
    assert row2["attendance_rate"] is None
    assert row2["study_hours_per_week"] == 12.0

    # Check idempotency on re-run
    res_second = migrate_csv_to_sqlite(csv_path=csv_path, conn=conn)
    assert res_second["inserted"] == 0
    assert res_second["skipped"] == 4
    assert res_second["total_in_db"] == 3

    conn.close()
