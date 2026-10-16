"""
Database Initialization Script.
Creates tables, applies schema constraints, and migrates initial student data from data/student_data.csv.
"""

import os
import sys
from src.db.connection import get_db_connection, get_db_path
from src.db.schema import create_schema
from src.db.migrate import migrate_csv_to_sqlite


def init_database(db_path=None, csv_path=None):
    print("=" * 65)
    print("  STUDENT ACADEMIC SUCCESS PREDICTION SYSTEM - DB SETUP  ")
    print("=" * 65)

    path = get_db_path(db_path)
    print(f"[*] Target SQLite Database: {path}")

    conn = get_db_connection(path)
    try:
        print("[*] Creating database schema & indexes...")
        create_schema(conn)
        print("[+] Schema initialized successfully.")

        print("[*] Importing records from student_data.csv...")
        res = migrate_csv_to_sqlite(csv_path=csv_path, conn=conn)
        print(f"[+] Total rows in CSV:  {res['total_csv_rows']}")
        print(f"[+] New rows inserted:  {res['inserted']}")
        print(f"[+] Existing / Skipped: {res['skipped']}")
        print(f"[+] Parsing errors:     {res['errors']}")
        print(f"[+] Total in Database:  {res['total_in_db']}")
        print("[+] Database initialization complete!")
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
