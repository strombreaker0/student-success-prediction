"""
Student Management Blueprint Routes:
Handles student list, individual profiles, academic trajectories, CRUD,
CSV export, ReportLab PDF generation, and atomic CSV bulk upload.
"""

import io
import csv
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, abort
from flask_login import login_required, current_user
from src.services.student_service import (
    list_students, get_student_by_id, add_student, update_student,
    delete_student, export_students_to_csv
)
from src.services.prediction_service import get_prediction_history
from src.services.intervention_service import list_interventions
from src.services.academic_history_service import get_student_academic_history
from src.services.pdf_service import generate_student_pdf_report
from src.services.audit_service import log_audit_event
from src.db.connection import get_db_context, get_db_connection
from flask_app.forms import StudentForm, InterventionForm
from flask_app.security import faculty_or_admin_required, admin_required, no_cache, get_client_ip

students_bp = Blueprint('students', __name__, template_folder='../../templates/students')


@students_bp.route('/students')
@login_required
@no_cache
def index():
    if current_user.is_student():
        sid = current_user.linked_student_id
        if sid:
            return redirect(url_for('students.detail', student_id=sid))
        flash("Your student account is not yet linked to an academic profile.", "warning")
        return redirect(url_for('main.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_q = request.args.get('q', '').strip()
    outcome_f = request.args.get('outcome', 'All').strip()

    offset = (page - 1) * per_page
    records, total_count = list_students(
        search_query=search_q,
        outcome_filter=outcome_f,
        requesting_user=current_user.to_dict(),
        limit=per_page,
        offset=offset
    )

    total_pages = max(1, (total_count + per_page - 1) // per_page)

    return render_template(
        'students/list.html',
        students=records,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
        search_query=search_q,
        outcome_filter=outcome_f,
        user=current_user
    )


@students_bp.route('/students/new', methods=['GET', 'POST'])
@login_required
@faculty_or_admin_required
@no_cache
def create():
    form = StudentForm()
    if form.validate_on_submit():
        data = {
            "student_id": form.student_id.data.strip().upper(),
            "attendance_rate": form.attendance_rate.data,
            "study_hours_per_week": form.study_hours_per_week.data,
            "previous_scores": form.previous_scores.data,
            "assignment_completion_rate": form.assignment_completion_rate.data,
            "tutoring_sessions": form.tutoring_sessions.data,
            "sleep_hours": form.sleep_hours.data,
            "extracurricular": int(form.extracurricular.data),
            "internet_access": int(form.internet_access.data),
            "final_exam_score": form.final_exam_score.data if form.final_exam_score.data is not None else None,
            "passed": int(form.passed.data) if (form.passed.data and form.passed.data != "") else None
        }

        ok, msg, created = add_student(data, requesting_user=current_user.to_dict())
        if ok:
            log_audit_event(
                current_user.username,
                "STUDENT_CREATE",
                target=f"student_id={data['student_id']}",
                user_id=current_user.id,
                ip_address=get_client_ip()
            )
            flash(f"Student record '{data['student_id']}' added successfully.", "success")
            return redirect(url_for('students.detail', student_id=data['student_id']))
        else:
            flash(msg, "danger")

    return render_template('students/form.html', form=form, title="Register New Student", is_edit=False)


@students_bp.route('/students/<student_id>')
@login_required
@no_cache
def detail(student_id):
    clean_id = str(student_id).strip().upper()

    # IDOR Prevention Check
    if not current_user.can_view_student(clean_id):
        abort(403)

    student = get_student_by_id(clean_id, requesting_user=current_user.to_dict())
    if not student:
        flash(f"Student '{clean_id}' not found.", "warning")
        return redirect(url_for('students.index') if current_user.can_manage_students() else url_for('main.dashboard'))

    # Load recent predictions, interventions, and 4-year academic transcript
    predictions = get_prediction_history(student_id=clean_id, limit=5)
    interventions, _ = list_interventions(student_id=clean_id, requesting_user=current_user.to_dict(), limit=10)
    transcript = get_student_academic_history(clean_id)
    intervention_form = InterventionForm(student_id=clean_id)

    return render_template(
        'students/detail.html',
        student=student,
        predictions=predictions,
        interventions=interventions,
        transcript=transcript,
        intervention_form=intervention_form,
        user=current_user
    )


@students_bp.route('/students/<student_id>/edit', methods=['GET', 'POST'])
@login_required
@faculty_or_admin_required
@no_cache
def edit(student_id):
    clean_id = str(student_id).strip().upper()
    if not current_user.can_modify_student(clean_id):
        abort(403)

    student = get_student_by_id(clean_id, requesting_user=current_user.to_dict())
    if not student:
        abort(404)

    form = StudentForm()
    if request.method == 'GET':
        form.student_id.data = student["student_id"]
        form.attendance_rate.data = student["attendance_rate"]
        form.study_hours_per_week.data = student["study_hours_per_week"]
        form.previous_scores.data = student["previous_scores"]
        form.assignment_completion_rate.data = student["assignment_completion_rate"]
        form.tutoring_sessions.data = student["tutoring_sessions"]
        form.sleep_hours.data = student["sleep_hours"]
        form.extracurricular.data = str(student["extracurricular"]) if student["extracurricular"] is not None else "0"
        form.internet_access.data = str(student["internet_access"]) if student["internet_access"] is not None else "1"
        form.final_exam_score.data = student["final_exam_score"]
        form.passed.data = str(student["passed"]) if student["passed"] is not None else ""

    if form.validate_on_submit():
        data = {
            "attendance_rate": form.attendance_rate.data,
            "study_hours_per_week": form.study_hours_per_week.data,
            "previous_scores": form.previous_scores.data,
            "assignment_completion_rate": form.assignment_completion_rate.data,
            "tutoring_sessions": form.tutoring_sessions.data,
            "sleep_hours": form.sleep_hours.data,
            "extracurricular": int(form.extracurricular.data),
            "internet_access": int(form.internet_access.data),
            "final_exam_score": form.final_exam_score.data if form.final_exam_score.data is not None else None,
            "passed": int(form.passed.data) if (form.passed.data and form.passed.data != "") else None
        }

        ok, msg, updated = update_student(clean_id, data, requesting_user=current_user.to_dict())
        if ok:
            log_audit_event(
                current_user.username,
                "STUDENT_UPDATE",
                target=f"student_id={clean_id}",
                user_id=current_user.id,
                ip_address=get_client_ip()
            )
            flash(f"Student record '{clean_id}' updated successfully.", "success")
            return redirect(url_for('students.detail', student_id=clean_id))
        else:
            flash(msg, "danger")

    return render_template('students/form.html', form=form, title=f"Edit Student {clean_id}", is_edit=True)


@students_bp.route('/students/<student_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(student_id):
    clean_id = str(student_id).strip().upper()
    if not current_user.can_delete_student_record(clean_id):
        abort(403)

    ok, msg = delete_student(clean_id, requesting_user=current_user.to_dict())
    if ok:
        log_audit_event(
            current_user.username,
            "STUDENT_DELETE",
            target=f"student_id={clean_id}",
            user_id=current_user.id,
            ip_address=get_client_ip()
        )
        flash(f"Student record '{clean_id}' was deleted.", "info")
    else:
        flash(msg, "danger")
    return redirect(url_for('students.index'))


@students_bp.route('/students/export')
@login_required
@faculty_or_admin_required
def export_csv():
    search_q = request.args.get('q', '').strip()
    outcome_f = request.args.get('outcome', 'All').strip()
    csv_str = export_students_to_csv(search_query=search_q, outcome_filter=outcome_f, requesting_user=current_user.to_dict())

    log_audit_event(
        current_user.username,
        "REPORT_EXPORT",
        target=f"format=csv, query={search_q}",
        user_id=current_user.id,
        ip_address=get_client_ip()
    )

    return Response(
        csv_str,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=students_roster_export.csv"}
    )


@students_bp.route('/students/<student_id>/report/pdf')
@login_required
@no_cache
def export_pdf(student_id):
    clean_id = str(student_id).strip().upper()
    if not current_user.can_view_student(clean_id):
        abort(403)

    try:
        pdf_bytes = generate_student_pdf_report(clean_id, requesting_user=current_user.to_dict())
        log_audit_event(
            current_user.username,
            "REPORT_EXPORT",
            target=f"format=pdf, student_id={clean_id}",
            user_id=current_user.id,
            ip_address=get_client_ip()
        )
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"inline; filename=student_{clean_id}_assessment.pdf"}
        )
    except Exception as e:
        flash(f"Error generating PDF dossier: {e}", "danger")
        return redirect(url_for('students.detail', student_id=clean_id))


@students_bp.route('/students/bulk-upload', methods=['GET', 'POST'])
@login_required
@faculty_or_admin_required
def bulk_upload():
    """
    Priority 2: Bulk CSV upload with row-level validation and atomic rollback on failure.
    """
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.csv'):
            flash("Please upload a valid CSV file.", "danger")
            return render_template('students/bulk_upload.html')

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
            reader = csv.DictReader(stream)
            rows = list(reader)
        except Exception as e:
            flash(f"Could not parse CSV file: {e}", "danger")
            return render_template('students/bulk_upload.html')

        if not rows:
            flash("The uploaded CSV file contains no data rows.", "warning")
            return render_template('students/bulk_upload.html')

        required_cols = ['student_id', 'attendance_rate', 'study_hours_per_week', 'previous_scores', 'assignment_completion_rate']
        missing = [c for c in required_cols if c not in reader.fieldnames]
        if missing:
            flash(f"CSV missing mandatory columns: {', '.join(missing)}", "danger")
            return render_template('students/bulk_upload.html')

        # Row-level validation
        validation_errors = []
        validated_records = []

        for row_idx, r in enumerate(rows, start=2):
            sid = str(r.get('student_id', '')).strip().upper()
            if not sid:
                validation_errors.append(f"Row {row_idx}: Missing student_id.")
                continue

            if current_user.is_demo_admin() and not sid.startswith("STU_DEMO"):
                validation_errors.append(f"Row {row_idx} ({sid}): Demo Administrator cannot import or modify non-demo records (must begin with STU_DEMO).")
                continue

            try:
                att = float(r.get('attendance_rate'))
                if not (0.0 <= att <= 100.0):
                    validation_errors.append(f"Row {row_idx} ({sid}): Attendance rate must be between 0 and 100.")
            except (ValueError, TypeError):
                validation_errors.append(f"Row {row_idx} ({sid}): Invalid attendance rate value.")
                continue

            try:
                study = float(r.get('study_hours_per_week'))
                if not (0.0 <= study <= 168.0):
                    validation_errors.append(f"Row {row_idx} ({sid}): Study hours must be between 0 and 168.")
            except (ValueError, TypeError):
                validation_errors.append(f"Row {row_idx} ({sid}): Invalid study hours value.")
                continue

            try:
                prev = float(r.get('previous_scores'))
                assign = float(r.get('assignment_completion_rate'))
                tutor = int(r.get('tutoring_sessions', 0))
                sleep = float(r.get('sleep_hours', 7.0))
                extra = int(r.get('extracurricular', 0))
                net = int(r.get('internet_access', 1))
            except (ValueError, TypeError) as num_err:
                validation_errors.append(f"Row {row_idx} ({sid}): Numeric formatting error: {num_err}")
                continue

            validated_records.append({
                "student_id": sid,
                "attendance_rate": att,
                "study_hours_per_week": study,
                "previous_scores": prev,
                "assignment_completion_rate": assign,
                "tutoring_sessions": tutor,
                "sleep_hours": sleep,
                "extracurricular": extra,
                "internet_access": net
            })

        if validation_errors:
            flash(f"Validation failed with {len(validation_errors)} error(s). No records imported (atomic integrity).", "danger")
            return render_template('students/bulk_upload.html', errors=validation_errors[:15])

        # Atomic commit: All or nothing
        try:
            with get_db_context() as conn:
                cursor = conn.cursor()
                for rec in validated_records:
                    cursor.execute("""
                    INSERT INTO students (
                        student_id, attendance_rate, study_hours_per_week, previous_scores,
                        assignment_completion_rate, tutoring_sessions, sleep_hours,
                        extracurricular, internet_access
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student_id) DO UPDATE SET
                        attendance_rate = excluded.attendance_rate,
                        study_hours_per_week = excluded.study_hours_per_week,
                        previous_scores = excluded.previous_scores,
                        assignment_completion_rate = excluded.assignment_completion_rate,
                        tutoring_sessions = excluded.tutoring_sessions,
                        sleep_hours = excluded.sleep_hours,
                        extracurricular = excluded.extracurricular,
                        internet_access = excluded.internet_access,
                        updated_at = CURRENT_TIMESTAMP;
                    """, (
                        rec['student_id'], rec['attendance_rate'], rec['study_hours_per_week'],
                        rec['previous_scores'], rec['assignment_completion_rate'],
                        rec['tutoring_sessions'], rec['sleep_hours'],
                        rec['extracurricular'], rec['internet_access']
                    ))

            log_audit_event(
                current_user.username,
                "STUDENT_BULK_UPLOAD",
                target=f"count={len(validated_records)}",
                user_id=current_user.id,
                ip_address=get_client_ip()
            )
            flash(f"Successfully processed and imported {len(validated_records)} student records atomically.", "success")
            return redirect(url_for('students.index'))
        except Exception as e:
            flash(f"Database transaction rolled back due to error: {e}", "danger")
            return render_template('students/bulk_upload.html')

    return render_template('students/bulk_upload.html')
