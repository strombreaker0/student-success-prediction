"""
Database connection manager for SQLite.
Configured for multi-threaded Streamlit usage with WAL mode and foreign keys enabled.
"""

import os
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "database", "student_success.db")


def get_db_path(custom_path=None):
    if custom_path:
        return custom_path
    return os.environ.get("STUDENT_DB_PATH", DEFAULT_DB_PATH)


def get_db_connection(db_path=None):
    """
    Returns an open SQLite connection configured with Row factory,
    foreign keys, and WAL journal mode for concurrent read access.
    """
    path = get_db_path(db_path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def get_db_context(db_path=None):
    """
    Context manager for database transactions.
    Automatically commits on success or rolls back on exception.
    """
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
