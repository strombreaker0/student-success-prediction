"""
Model Transparency & System Architecture Blueprint Routes:
Presents empirical model evaluation metrics, confusion matrices, dataset limitations,
and technical architectural specifications from the field project report.
"""

import os
import json
import pandas as pd
from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from flask_app.security import faculty_or_admin_required, no_cache

transparency_bp = Blueprint('transparency', __name__, template_folder='../../templates/transparency')


from src.services.prediction_service import MODELS_DIR


@transparency_bp.route('/transparency')
@login_required
@faculty_or_admin_required
@no_cache
def index():
    metrics_path = os.path.join(MODELS_DIR, 'evaluation_metrics.json')
    coef_path = os.path.join(MODELS_DIR, 'logistic_regression_coefficients.csv')

    metrics_data = {}
    coefficients = []
    file_error = None

    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, 'r', encoding='utf-8') as f:
                metrics_data = json.load(f)
        except Exception as e:
            file_error = f"Failed to read evaluation metrics file: {e}"
    else:
        file_error = "Model evaluation metrics artifact (evaluation_metrics.json) is missing. Train models to generate it."

    if os.path.exists(coef_path):
        try:
            df_coef = pd.read_csv(coef_path)
            coefficients = df_coef.to_dict(orient='records')
        except Exception as e:
            pass

    return render_template(
        'transparency/index.html',
        metrics=metrics_data,
        coefficients=coefficients,
        file_error=file_error,
        dataset_info={
            "total_samples": 1200,
            "train_samples": 960,
            "test_samples": 240,
            "train_split": "80% Stratified",
            "test_split": "20% Stratified",
            "features_count": 8,
            "target": "passed (Binary: 0=Fail, 1=Pass)"
        },
        user=current_user
    )


@transparency_bp.route('/transparency/about')
@login_required
@no_cache
def about():
    """System Architecture, ER Schema, and Academic Credentials."""
    return render_template(
        'transparency/about.html',
        credentials={
            "name": "Asmita Chandram Kumbar",
            "class": "Second Year B.Sc. Computer Science (SYBSc CS)",
            "roll_no": "SI1161",
            "year": "2nd Year",
            "project_title": "Predicting Student Academic Success and Exam Outcomes Using Supervised Machine Learning"
        },
        user=current_user
    )
