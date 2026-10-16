"""
Predictions Blueprint Routes:
Handles real-time ML inference with explainability (top 3 contributing factors),
batch cohort CSV screening, and the What-If academic scenario simulator.
"""

import io
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, abort
from flask_login import login_required, current_user
from src.services.prediction_service import (
    predict_student, run_batch_screening, get_available_models,
    get_prediction_history
)
from src.services.student_service import get_student_by_id
from src.services.audit_service import log_audit_event
from flask_app.forms import PredictionForm, BatchUploadForm
from flask_app.security import faculty_or_admin_required, no_cache, get_client_ip

predictions_bp = Blueprint('predictions', __name__, template_folder='../../templates/predictions')


@predictions_bp.route('/predictions/new', methods=['GET', 'POST'])
@login_required
@no_cache
def predict():
    form = PredictionForm()

    # Pre-populate if student_id is passed in query args
    pre_student_id = request.args.get('student_id')
    if request.method == 'GET' and pre_student_id:
        student = get_student_by_id(pre_student_id.strip().upper(), requesting_user=current_user.to_dict())
        if student:
            form.student_id.data = student["student_id"]
            form.attendance_rate.data = student["attendance_rate"]
            form.study_hours_per_week.data = student["study_hours_per_week"]
            form.previous_scores.data = student["previous_scores"]
            form.assignment_completion_rate.data = student["assignment_completion_rate"]
            form.tutoring_sessions.data = student["tutoring_sessions"]
            form.sleep_hours.data = student["sleep_hours"]
            form.extracurricular.data = str(student["extracurricular"]) if student["extracurricular"] is not None else "0"
            form.internet_access.data = str(student["internet_access"]) if student["internet_access"] is not None else "1"

    prediction_result = None
    if form.validate_on_submit():
        # Prevent IDOR for student role
        target_sid = form.student_id.data.strip().upper() if form.student_id.data else None
        if current_user.is_student() and target_sid:
            if not current_user.can_view_student(target_sid):
                abort(403)

        student_payload = {
            "student_id": target_sid,
            "attendance_rate": form.attendance_rate.data,
            "study_hours_per_week": form.study_hours_per_week.data,
            "previous_scores": form.previous_scores.data,
            "assignment_completion_rate": form.assignment_completion_rate.data,
            "tutoring_sessions": form.tutoring_sessions.data,
            "sleep_hours": form.sleep_hours.data,
            "extracurricular": int(form.extracurricular.data),
            "internet_access": int(form.internet_access.data)
        }

        try:
            prediction_result = predict_student(
                student_data=student_payload,
                model_name=form.model_name.data,
                actor_username=current_user.username,
                save_history=True if target_sid else False
            )

            log_audit_event(
                current_user.username,
                "PREDICTION_RUN",
                target=f"student={target_sid}, model={form.model_name.data}",
                user_id=current_user.id,
                ip_address=get_client_ip()
            )
            flash("Model inference completed with explainable factor breakdown.", "success")
        except Exception as e:
            flash(f"Prediction evaluation failed: {e}", "danger")

    return render_template(
        'predictions/predict.html',
        form=form,
        result=prediction_result,
        models=get_available_models(),
        user=current_user
    )


@predictions_bp.route('/predictions/batch', methods=['GET', 'POST'])
@login_required
@faculty_or_admin_required
@no_cache
def batch():
    form = BatchUploadForm()
    batch_results = None
    csv_download_token = None

    if form.validate_on_submit():
        file = form.file.data
        if not file.filename.endswith('.csv'):
            flash("Please upload a CSV file.", "danger")
            return render_template('predictions/batch.html', form=form)

        try:
            df = pd.read_csv(file)
            result_df, errors = run_batch_screening(
                df=df,
                model_name=form.model_name.data,
                actor_username=current_user.username,
                save_to_db=form.save_to_database.data
            )
            if errors:
                for err in errors:
                    flash(f"Batch screening error: {err}", "danger")
            else:
                batch_results = result_df.to_dict(orient="records")
                log_audit_event(
                    current_user.username,
                    "BATCH_SCREENING_RUN",
                    target=f"rows={len(result_df)}, model={form.model_name.data}",
                    user_id=current_user.id,
                    ip_address=get_client_ip()
                )
                flash(f"Successfully screened {len(result_df)} students using {form.model_name.data}.", "success")
        except Exception as e:
            flash(f"Error processing CSV: {e}", "danger")

    return render_template(
        'predictions/batch.html',
        form=form,
        results=batch_results,
        user=current_user
    )


@predictions_bp.route('/predictions/simulator', methods=['GET', 'POST'])
@login_required
@no_cache
def simulator():
    """
    Priority 2: What-If Academic Scenario Simulator.
    Allows interactive exploration of parameter adjustments on exam risk trajectory.
    Explicitly labeled as simulation and NEVER saved to prediction history.
    """
    # Default values reflecting cohort medians
    simulation_inputs = {
        "attendance_rate": float(request.args.get("attendance_rate", 75.0)),
        "study_hours_per_week": float(request.args.get("study_hours_per_week", 14.0)),
        "previous_scores": float(request.args.get("previous_scores", 65.0)),
        "assignment_completion_rate": float(request.args.get("assignment_completion_rate", 80.0)),
        "tutoring_sessions": int(request.args.get("tutoring_sessions", 2)),
        "sleep_hours": float(request.args.get("sleep_hours", 7.0)),
        "extracurricular": int(request.args.get("extracurricular", 1)),
        "internet_access": int(request.args.get("internet_access", 1)),
        "model_name": request.args.get("model_name", "Logistic Regression")
    }

    try:
        # Run real model inference with save_history=False strictly enforced
        sim_result = predict_student(
            student_data=simulation_inputs,
            model_name=simulation_inputs["model_name"],
            actor_username="simulator",
            save_history=False
        )
    except Exception as e:
        sim_result = None
        flash(f"Simulation engine error: {e}", "danger")

    return render_template(
        'predictions/simulator.html',
        inputs=simulation_inputs,
        result=sim_result,
        user=current_user
    )
