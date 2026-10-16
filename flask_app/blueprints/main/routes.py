"""
Main Dashboard & Landing Blueprint Routes:
Renders high-level institutional KPIs, Needs Attention student roster,
and overdue intervention alerts.
"""

from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from src.services.student_service import get_dashboard_summary_metrics, get_student_by_id
from src.services.prediction_service import get_prediction_history
from src.services.intervention_service import get_overdue_interventions
from src.db.connection import get_db_connection
from flask_app.security import no_cache

main_bp = Blueprint('main', __name__, template_folder='../../templates/dashboard')


@main_bp.route('/')
@main_bp.route('/demo')
@main_bp.route('/demo/dashboard')
def demo_dashboard():
    """
    Dedicated Admin Demo Dashboard.
    Opens directly on the homepage (/) or demo routes (/demo, /demo/dashboard) without requiring login.
    Strictly isolated: queries ONLY synthetic demo records (student_id LIKE 'STU_DEMO%').
    Real student records, real user accounts, and passwords are never queried or exposed.
    All real admin actions remain protected by authentication and RBAC.
    """
    # Ensure synthetic demo cohort exists in the database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM students WHERE student_id LIKE 'STU_DEMO%';")
        demo_count = cursor.fetchone()[0]
        if demo_count == 0:
            from src.services.demo_service import provision_demo_accounts
            provision_demo_accounts(conn=conn)
    finally:
        conn.close()

    demo_user_dict = {
        "id": 0,
        "username": "demo_admin",
        "email": "demo.admin@institution.edu",
        "role": "admin",
        "full_name": "Institutional Demo Administrator",
        "is_demo_admin": True,
        "is_demo_student": False
    }

    # Synthetic demo metrics
    metrics = get_dashboard_summary_metrics(requesting_user=demo_user_dict)
    overdue_interventions = get_overdue_interventions(requesting_user=demo_user_dict)
    recent_predictions = get_prediction_history(limit=6, requesting_user=demo_user_dict)

    # Synthetic "Needs Attention" student roster
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT student_id, attendance_rate, study_hours_per_week, previous_scores, 
               assignment_completion_rate, passed, final_exam_score
        FROM students
        WHERE ((attendance_rate IS NOT NULL AND attendance_rate < 75.0) OR passed = 0)
          AND student_id LIKE 'STU_DEMO%'
        ORDER BY 
            CASE WHEN attendance_rate IS NULL THEN 1 ELSE 0 END,
            attendance_rate ASC, 
            study_hours_per_week ASC
        LIMIT 10;
        """)
        needs_attention = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    from flask_app.models import DemoAdminPersona
    demo_persona = DemoAdminPersona()

    return render_template(
        'dashboard/demo_index.html',
        metrics=metrics,
        needs_attention=needs_attention,
        overdue_interventions=overdue_interventions,
        recent_predictions=recent_predictions,
        user=current_user if current_user.is_authenticated else demo_persona,
        is_demo_dashboard=True
    )


@main_bp.route('/dashboard')
@login_required
@no_cache
def dashboard():
    # If the user is a student, route directly to their personalized student portal view
    if current_user.is_student():
        sid = current_user.linked_student_id
        if sid:
            return redirect(url_for('students.detail', student_id=sid))
        return render_template(
            'dashboard/student_unlinked.html',
            user=current_user
        )

    # For Faculty and Administrator: Executive Educational Analytics Dashboard
    metrics = get_dashboard_summary_metrics(requesting_user=current_user.to_dict())
    overdue_interventions = get_overdue_interventions(requesting_user=current_user.to_dict())
    recent_predictions = get_prediction_history(limit=6, requesting_user=current_user.to_dict())

    # Priority 2: "Needs attention" panel - Highest-risk students first (attendance < 75% or fail likelihood)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if current_user.is_demo_admin():
            cursor.execute("""
            SELECT student_id, attendance_rate, study_hours_per_week, previous_scores, 
                   assignment_completion_rate, passed, final_exam_score
            FROM students
            WHERE ((attendance_rate IS NOT NULL AND attendance_rate < 75.0) OR passed = 0)
              AND student_id LIKE 'STU_DEMO%'
            ORDER BY 
                CASE WHEN attendance_rate IS NULL THEN 1 ELSE 0 END,
                attendance_rate ASC, 
                study_hours_per_week ASC
            LIMIT 10;
            """)
        else:
            cursor.execute("""
            SELECT student_id, attendance_rate, study_hours_per_week, previous_scores, 
                   assignment_completion_rate, passed, final_exam_score
            FROM students
            WHERE (attendance_rate IS NOT NULL AND attendance_rate < 75.0) OR passed = 0
            ORDER BY 
                CASE WHEN attendance_rate IS NULL THEN 1 ELSE 0 END,
                attendance_rate ASC, 
                study_hours_per_week ASC
            LIMIT 10;
            """)
        needs_attention = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    return render_template(
        'dashboard/index.html',
        metrics=metrics,
        needs_attention=needs_attention,
        overdue_interventions=overdue_interventions,
        recent_predictions=recent_predictions,
        user=current_user
    )


@main_bp.route('/search')
def global_search():
    """Global search across students, respecting role permissions and demo isolation."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if not current_user.is_authenticated or (hasattr(current_user, 'is_demo_admin') and current_user.is_demo_admin()):
            # Anonymous visitors and Demo Admin can ONLY search synthetic demo records
            cursor.execute("""
            SELECT student_id, attendance_rate, passed
            FROM students
            WHERE student_id LIKE ? AND student_id LIKE 'STU_DEMO%'
            ORDER BY student_id ASC
            LIMIT 8;
            """, (f"%{query.upper()}%",))
        elif current_user.is_student():
            sid = current_user.linked_student_id
            if sid and query.upper() in sid.upper():
                return jsonify([{"type": "student", "label": f"My Profile ({sid})", "url": url_for('students.detail', student_id=sid)}])
            return jsonify([])
        else:
            # Authenticated Faculty / Admin search across full cohort
            cursor.execute("""
            SELECT student_id, attendance_rate, passed
            FROM students
            WHERE student_id LIKE ?
            ORDER BY student_id ASC
            LIMIT 8;
            """, (f"%{query.upper()}%",))
        results = []
        for r in cursor.fetchall():
            results.append({
                "type": "student",
                "label": f"Student {r['student_id']} (Att: {r['attendance_rate']}%)",
                "url": url_for('students.detail', student_id=r['student_id'])
            })
        return jsonify(results)
    finally:
        conn.close()
