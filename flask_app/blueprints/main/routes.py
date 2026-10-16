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
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


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
    metrics = get_dashboard_summary_metrics()
    overdue_interventions = get_overdue_interventions(requesting_user=current_user.to_dict())
    recent_predictions = get_prediction_history(limit=6)

    # Priority 2: "Needs attention" panel - Highest-risk students first (attendance < 75% or fail likelihood)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
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
@login_required
def global_search():
    """Global search across students, respecting role permissions."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if current_user.is_student():
            sid = current_user.linked_student_id
            if sid and query.upper() in sid.upper():
                return jsonify([{"type": "student", "label": f"My Profile ({sid})", "url": url_for('students.detail', student_id=sid)}])
            return jsonify([])

        # Faculty / Admin search
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
