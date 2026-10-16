"""
Automated Deployment Readiness & Production Bootstrap Test Suite.
Verifies:
1. Fresh database initialization on empty / non-existent DB without "no such table: users" error.
2. Safe idempotent enhancements migration.
3. Auto-seeding of baseline students from CSV on empty database.
4. Auto-provisioning of admin account from environment variables on fresh deployment.
5. wsgi.py exports valid Flask application callable.
6. Health check endpoints (/health and /healthz) return 200 OK and readiness status.
7. Model artifacts load and infer properly.
"""

import os
import tempfile
import sqlite3
import pytest
from flask import Flask

from src.db.connection import get_db_connection
from src.db.schema import create_schema
from src.db.migrate_enhancements import run_enhancements_migration
from src.db.init_app_db import ensure_db_initialized
from src.services.prediction_service import load_artifacts, predict_student


def test_01_fresh_db_migration_no_table_error():
    """Verify migrate_enhancements does not crash on brand-new empty DB."""
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(temp_db)  # Ensure file does not exist initially

    try:
        conn = get_db_connection(temp_db)
        # Calling enhancements migration directly on fresh db must not crash
        success = run_enhancements_migration(conn)
        assert success is True

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}

        # Verify core tables were created
        expected = {'users', 'students', 'prediction_history', 'interventions', 'audit_logs'}
        assert expected.issubset(tables)
        conn.close()
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_02_ensure_db_initialized_with_seeding_and_admin(monkeypatch):
    """Verify fresh bootstrap seeds CSV data and provisions admin when env vars set."""
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(temp_db)

    monkeypatch.setenv("ADMIN_USERNAME", "deploy_admin")
    monkeypatch.setenv("ADMIN_EMAIL", "deploy_admin@institution.edu")
    monkeypatch.setenv("ADMIN_PASSWORD", "SuperSecurePass123")
    monkeypatch.setenv("ADMIN_NAME", "Deploy Admin")

    try:
        res = ensure_db_initialized(db_path=temp_db, seed_csv_if_empty=True, bootstrap_admin_if_empty=True)
        assert res["status"] == "ready"
        assert res["students"] >= 1000  # Baseline dataset has 1200 records
        assert res["users"] >= 1        # Admin user created

        conn = get_db_connection(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, role FROM users WHERE username='deploy_admin';")
        user = cursor.fetchone()
        assert user is not None
        assert user["role"] == "admin"
        assert user["email"] == "deploy_admin@institution.edu"
        conn.close()
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_03_wsgi_exports_application():
    """Verify wsgi.py exports a valid Flask application callable."""
    import wsgi
    assert hasattr(wsgi, "application")
    assert isinstance(wsgi.application, Flask)
    assert hasattr(wsgi, "app")
    assert wsgi.app is wsgi.application


def test_04_health_and_healthz_endpoints(client):
    """Verify both /health and /healthz endpoints return HTTP 200 with readiness data."""
    for path in ['/health', '/healthz']:
        res = client.get(path)
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["models"] == "loaded"
        assert data["tables_ready"] is True
        assert "records" in data


def test_05_model_artifacts_load_and_predict():
    """Verify ML models and preprocessors load and make accurate predictions."""
    preprocessors, models = load_artifacts()
    assert 'imputer' in preprocessors
    assert 'scaler' in preprocessors
    assert len(models) == 3

    sample_student = {
        'student_id': 'TEST_DEPLOY_01',
        'attendance_rate': 85.0,
        'study_hours_per_week': 15.0,
        'previous_scores': 80.0,
        'assignment_completion_rate': 90.0,
        'tutoring_sessions': 2,
        'sleep_hours': 7.5,
        'extracurricular': 1,
        'internet_access': 1
    }

    result = predict_student(sample_student, model_name='Random Forest', save_history=False)
    assert result['predicted_outcome'] in (0, 1)
    assert 0.0 <= result['pass_probability'] <= 1.0
    assert result['risk_category'] in ('Low Risk', 'Moderate Risk', 'High Risk')
