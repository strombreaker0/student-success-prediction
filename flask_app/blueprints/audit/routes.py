"""
Audit Blueprint Routes:
Admin-only viewer for immutable system event traces with search, filtering, and pagination.
"""

from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user
from src.services.audit_service import list_audit_logs
from flask_app.security import admin_required, no_cache

audit_bp = Blueprint('audit', __name__, template_folder='../../templates/audit')


@audit_bp.route('/audit')
@login_required
@admin_required
@no_cache
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    search_q = request.args.get('q', '').strip()
    action_f = request.args.get('action', '').strip()
    user_f = request.args.get('username', '').strip()

    logs, total_count = list_audit_logs(
        search=search_q if search_q else None,
        action=action_f if action_f else None,
        username=user_f if user_f else None,
        page=page,
        per_page=per_page,
        requesting_user=current_user.to_dict()
    )

    total_pages = max(1, (total_count + per_page - 1) // per_page)

    distinct_actions = [
        "LOGIN_SUCCESS", "LOGIN_FAILURE", "LOGIN_RATE_LIMITED", "LOGOUT",
        "REGISTER_SUCCESS", "PASSWORD_CHANGE", "STUDENT_CREATE",
        "STUDENT_UPDATE", "STUDENT_DELETE", "STUDENT_BULK_UPLOAD",
        "PREDICTION_RUN", "BATCH_SCREENING_RUN", "INTERVENTION_CREATE",
        "INTERVENTION_UPDATE", "REPORT_EXPORT"
    ]

    return render_template(
        'audit/index.html',
        logs=logs,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
        search_query=search_q,
        action_filter=action_f,
        user_filter=user_f,
        actions=distinct_actions,
        user=current_user
    )
