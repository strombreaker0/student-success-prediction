"""
API Blueprint Routes:
Provides system readiness health checks, interactive simulation endpoints,
and analytical chart data.
"""

import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from src.db.connection import get_db_connection
from src.services.prediction_service import predict_student, load_artifacts

api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
@api_bp.route('/healthz')
def health():
    """
    Health check and readiness probe endpoint.
    Verifies SQLite database connectivity, core tables existence, and ML artifacts
    without exposing credentials or sensitive internals.
    """
    db_status = "unavailable"
    models_status = "unavailable"
    tables_ready = False
    student_count = 0
    user_count = 0
    status_code = 200

    # 1. Check Database Connectivity and Schema Tables
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        if cursor.fetchone()[0] == 1:
            db_status = "connected"

        # Verify core tables exist
        required_tables = {'users', 'students', 'prediction_history'}
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        if required_tables.issubset(existing_tables):
            tables_ready = True
            cursor.execute("SELECT COUNT(*) FROM students;")
            student_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]
        else:
            tables_ready = False
            db_status = "missing_tables"
            status_code = 503

        conn.close()
    except Exception as e:
        db_status = "error"
        tables_ready = False
        status_code = 503

    # 2. Check ML Preprocessors & Models
    try:
        preprocessors, models = load_artifacts()
        if 'imputer' in preprocessors and 'scaler' in preprocessors and len(models) >= 3:
            models_status = "loaded"
        else:
            models_status = "incomplete"
            status_code = 503
    except Exception as e:
        models_status = "unavailable"
        status_code = 503

    overall_status = "healthy" if (db_status == "connected" and tables_ready and models_status == "loaded") else "degraded"

    return jsonify({
        "status": overall_status,
        "database": db_status,
        "tables_ready": tables_ready,
        "models": models_status,
        "records": {
            "students": student_count,
            "users": user_count
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "AI-Based Student Academic Success Prediction System"
    }), status_code


@api_bp.route('/api/simulate', methods=['POST'])
@login_required
def simulate():
    """
    Priority 2: Simulation JSON endpoint for What-if sliders.
    Explicitly enforces save_history=False.
    """
    data = request.get_json() or {}
    try:
        sim_res = predict_student(
            student_data=data,
            model_name=data.get("model_name", "Logistic Regression"),
            actor_username="api_simulator",
            save_history=False
        )
        return jsonify({"success": True, "data": sim_res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route('/api/chart-data')
def chart_data():
    """
    Provides aggregated distributions for Chart.js dashboard visualizers.
    If requested by an unauthenticated visitor, demo admin, or with ?demo=1,
    strictly confines aggregation to synthetic demo records (student_id LIKE 'STU_DEMO%').
    """
    is_demo = (
        not current_user.is_authenticated
        or (hasattr(current_user, 'is_demo_admin') and current_user.is_demo_admin())
        or request.args.get('demo') == '1'
    )

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        demo_filter_where = "WHERE student_id LIKE 'STU_DEMO%'" if is_demo else ""
        demo_filter_and = "AND student_id LIKE 'STU_DEMO%'" if is_demo else ""

        # 1. Outcomes
        cursor.execute(f"SELECT passed, COUNT(*) FROM students {demo_filter_where} GROUP BY passed;")
        outcome_rows = cursor.fetchall()
        outcome_counts = {"Passed": 0, "Failed": 0, "Pending": 0}
        for r in outcome_rows:
            if r[0] == 1:
                outcome_counts["Passed"] = r[1]
            elif r[0] == 0:
                outcome_counts["Failed"] = r[1]
            else:
                outcome_counts["Pending"] = r[1]

        # 2. Attendance Bins
        cursor.execute(f"""
        SELECT 
            CASE 
                WHEN attendance_rate < 60 THEN '< 60%'
                WHEN attendance_rate BETWEEN 60 AND 74.9 THEN '60% - 74%'
                WHEN attendance_rate BETWEEN 75 AND 89.9 THEN '75% - 89%'
                ELSE '90% - 100%'
            END as att_bin,
            COUNT(*) as count,
            AVG(passed) as pass_rate
        FROM students
        WHERE attendance_rate IS NOT NULL {demo_filter_and}
        GROUP BY att_bin
        ORDER BY MIN(attendance_rate);
        """)
        att_bins = [{"bin": r["att_bin"], "count": r["count"], "pass_rate": round((r["pass_rate"] or 0) * 100, 1)} for r in cursor.fetchall()]

        return jsonify({
            "outcomes": outcome_counts,
            "attendance_bins": att_bins
        })
    finally:
        conn.close()
