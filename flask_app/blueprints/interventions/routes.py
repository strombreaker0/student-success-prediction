"""
Interventions Blueprint Routes:
Manages student remedial intervention workflows, tracking progress across
Open, In progress, and Resolved states with follow-up milestones.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from src.services.intervention_service import (
    list_interventions, create_intervention, update_intervention,
    get_overdue_interventions
)
from src.services.audit_service import log_audit_event
from flask_app.forms import InterventionForm
from flask_app.security import faculty_or_admin_required, no_cache, get_client_ip

interventions_bp = Blueprint('interventions', __name__, template_folder='../../templates/interventions')


@interventions_bp.route('/interventions')
@login_required
@no_cache
def index():
    status_filter = request.args.get('status', '').strip()
    student_id_filter = request.args.get('student_id', '').strip()
    search_q = request.args.get('q', '').strip()

    # Prevent student IDOR
    if current_user.is_student():
        student_id_filter = current_user.linked_student_id

    records, total_count = list_interventions(
        student_id=student_id_filter,
        status=status_filter if status_filter else None,
        search=search_q if search_q else None,
        requesting_user=current_user.to_dict(),
        limit=100
    )

    overdue_count = len(get_overdue_interventions(requesting_user=current_user.to_dict()))
    form = InterventionForm()

    return render_template(
        'interventions/index.html',
        interventions=records,
        total_count=total_count,
        overdue_count=overdue_count,
        status_filter=status_filter,
        student_id_filter=student_id_filter,
        search_query=search_q,
        form=form,
        user=current_user
    )


@interventions_bp.route('/interventions/new', methods=['POST'])
@login_required
@faculty_or_admin_required
def create():
    form = InterventionForm()
    if form.validate_on_submit():
        ok, msg, created = create_intervention(
            student_id=form.student_id.data.strip().upper(),
            title=form.title.data.strip(),
            description=form.description.data.strip() if form.description.data else "",
            follow_up_date=form.follow_up_date.data.strip() if form.follow_up_date.data else None,
            created_by=current_user.full_name or current_user.username,
            requesting_user=current_user.to_dict()
        )
        if ok:
            log_audit_event(
                current_user.username,
                "INTERVENTION_CREATE",
                target=f"student={form.student_id.data}, title={form.title.data}",
                user_id=current_user.id,
                ip_address=get_client_ip()
            )
            flash("Remedial intervention logged successfully.", "success")
        else:
            flash(msg, "danger")

        # Redirect back to referring page or interventions list
        ref = request.referrer
        if ref and "/students/" in ref:
            return redirect(ref)
        return redirect(url_for('interventions.index'))

    flash("Please fill in all required intervention fields.", "danger")
    return redirect(url_for('interventions.index'))


@interventions_bp.route('/interventions/<int:intervention_id>/update', methods=['POST'])
@login_required
@faculty_or_admin_required
def update(intervention_id):
    status = request.form.get('status')
    follow_up_date = request.form.get('follow_up_date')
    description = request.form.get('description')

    ok, msg, updated = update_intervention(
        intervention_id=intervention_id,
        status=status,
        follow_up_date=follow_up_date,
        description=description,
        requesting_user=current_user.to_dict()
    )

    if ok:
        log_audit_event(
            current_user.username,
            "INTERVENTION_UPDATE",
            target=f"id={intervention_id}, status={status}",
            user_id=current_user.id,
            ip_address=get_client_ip()
        )
        flash("Intervention updated successfully.", "success")
    else:
        flash(msg, "danger")

    return redirect(request.referrer or url_for('interventions.index'))
