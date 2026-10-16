"""
Database Initialization Script.
Creates tables, applies schema constraints, and migrates initial student data from data/student_data.csv.
"""

import os
import sys
from src.db.connection import get_db_connection, get_db_path
from src.db.init_app_db import ensure_db_initialized


def init_database(db_path=None, csv_path=None):
    print("=" * 65)
    print("  STUDENT ACADEMIC SUCCESS PREDICTION SYSTEM - DB SETUP  ")
    print("=" * 65)

    path = get_db_path(db_path)
    print(f"[*] Target SQLite Database: {path}")

    res = ensure_db_initialized(db_path=path)
    print(f"[+] Total students in Database: {res['students']}")
    print(f"[+] Total users in Database:    {res['users']}")
    print("[+] Database initialization complete!")


if __name__ == "__main__":
    init_database()
