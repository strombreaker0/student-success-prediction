"""
Prediction and ML Inference Service.
Integrates trained model artifacts (Logistic Regression, Decision Tree, Random Forest)
with preprocessing pipeline (imputer, scaler), computes risk categories, generates
personalized academic interventions, and logs prediction history in SQLite.
"""

import os
import json
import logging
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    'attendance_rate',
    'study_hours_per_week',
    'previous_scores',
    'assignment_completion_rate',
    'tutoring_sessions',
    'sleep_hours',
    'extracurricular',
    'internet_access'
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# Cache for models and scalers
_PREPROCESSORS = {}
_MODELS = {}


def load_artifacts():
    """Loads and caches the preprocessors and trained models."""
    global _PREPROCESSORS, _MODELS

    if not _PREPROCESSORS:
        imputer_path = os.path.join(MODELS_DIR, 'imputer.joblib')
        scaler_path = os.path.join(MODELS_DIR, 'scaler.joblib')

        if not os.path.exists(imputer_path) or not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Missing preprocessor artifacts in {MODELS_DIR}. Run train_models.py.")

        _PREPROCESSORS['imputer'] = joblib.load(imputer_path)
        _PREPROCESSORS['scaler'] = joblib.load(scaler_path)

    if not _MODELS:
        model_files = {
            'Logistic Regression': 'logistic_regression_model.joblib',
            'Decision Tree': 'decision_tree_model.joblib',
            'Random Forest': 'random_forest_model.joblib'
        }

        for name, filename in model_files.items():
            path = os.path.join(MODELS_DIR, filename)
            if os.path.exists(path):
                _MODELS[name] = joblib.load(path)
            else:
                logger.warning(f"Model artifact not found for {name}: {path}")

    return _PREPROCESSORS, _MODELS


def get_available_models() -> list[str]:
    _, models = load_artifacts()
    return list(models.keys())


def determine_risk_category(pass_prob: float) -> str:
    """Classifies risk level based on predicted pass likelihood."""
    if pass_prob >= 0.75:
        return "Low Risk"
    elif pass_prob >= 0.50:
        return "Moderate Risk"
    else:
        return "High Risk"


def generate_interventions(features: dict, predicted_outcome: int, pass_prob: float) -> list[str]:
    """
    Generates actionable, personalized academic intervention guidance
    based on the student's specific behavioral and academic metrics.
    """
    interventions = []

    att = features.get('attendance_rate')
    study = features.get('study_hours_per_week')
    prev = features.get('previous_scores')
    assign = features.get('assignment_completion_rate')
    tutor = features.get('tutoring_sessions')
    sleep = features.get('sleep_hours')

    if predicted_outcome == 1:
        if pass_prob >= 0.85:
            interventions.append("High Academic Trajectory: Student displays disciplined study and attendance patterns. Encourage enrollment in honors coursework, research projects, or peer tutoring leadership.")
        else:
            interventions.append("Borderline Pass Trajectory: Student is currently on track, but performance stability can be reinforced by optimizing study routines.")

    if att is not None and att < 75.0:
        interventions.append(f"Attendance Alert ({att:.1f}%): Below the 75% institutional threshold. Schedule mandatory academic counseling to identify commute or wellness factors and establish attendance recovery.")

    if study is not None and study < 12.0:
        interventions.append(f"Study Duration Deficit ({study:.1f} hrs/week): Sub-optimal independent study hours. Design a structured weekly timetable adding 3-4 focused revision blocks.")

    if assign is not None and assign < 75.0:
        interventions.append(f"Coursework Submission Alert ({assign:.1f}%): Delinquency in assignment submissions. Pair with an academic mentor and institute weekly milestone checkpoints.")

    if tutor is not None and tutor < 2:
        interventions.append("Remedial Support Recommended: Encourage participation in weekly faculty doubt-clearing sessions and peer-led study groups.")

    if prev is not None and prev < 50.0:
        interventions.append(f"Prior Exam Weakness ({prev:.1f}%): Historical foundational gaps require targeted concept revision in prerequisite topics.")

    if sleep is not None:
        if sleep < 6.0:
            interventions.append(f"Sleep Deprivation Flag ({sleep:.1f} hrs/night): Inadequate rest impairs cognitive retention. Provide educational guidance on sleep hygiene.")
        elif sleep > 10.0:
            interventions.append(f"Irregular Rest Pattern ({sleep:.1f} hrs/night): Excessive sleep may indicate low engagement or fatigue.")

    if not interventions:
        interventions.append("Maintain current academic habits and continue regular coursework monitoring.")

    return interventions


def predict_student(
    student_data: dict,
    model_name: str = "Logistic Regression",
    actor_username: str = "system",
    save_history: bool = True,
    conn = None
) -> dict:
    """
    Executes prediction for a student dictionary.
    Excludes final_exam_score and passed from input features.
    Saves prediction to database if student_id is present and save_history is True.
    """
    preprocessors, models = load_artifacts()

    if model_name not in models:
        raise ValueError(f"Selected model '{model_name}' is not available. Available: {list(models.keys())}")

    model = models[model_name]
    imputer = preprocessors['imputer']
    scaler = preprocessors['scaler']

    # Extract exactly the 8 feature columns
    raw_features = {}
    for col in FEATURE_COLS:
        val = student_data.get(col)
        try:
            raw_features[col] = float(val) if (val is not None and val != "") else np.nan
        except (ValueError, TypeError):
            raw_features[col] = np.nan

    input_df = pd.DataFrame([raw_features], columns=FEATURE_COLS)

    # Impute & Scale
    imputed_arr = imputer.transform(input_df)
    scaled_arr = scaler.transform(imputed_arr)

    # Predict
    pred = int(model.predict(scaled_arr)[0])
    if hasattr(model, 'predict_proba'):
        probs = model.predict_proba(scaled_arr)[0]
        fail_prob = float(probs[0])
        pass_prob = float(probs[1])
    else:
        pass_prob = 1.0 if pred == 1 else 0.0
        fail_prob = 1.0 - pass_prob

    risk_category = determine_risk_category(pass_prob)
    interventions = generate_interventions(raw_features, pred, pass_prob)

    result = {
        "student_id": student_data.get("student_id"),
        "model_name": model_name,
        "predicted_outcome": pred,
        "outcome_label": "Pass" if pred == 1 else "Fail",
        "pass_probability": round(pass_prob, 4),
        "fail_probability": round(fail_prob, 4),
        "pass_probability_pct": round(pass_prob * 100, 1),
        "fail_probability_pct": round(fail_prob * 100, 1),
        "risk_category": risk_category,
        "interventions": interventions,
        "predicted_by": actor_username,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # Save to prediction_history table if student_id exists
    sid = student_data.get("student_id")
    if sid and save_history:
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO prediction_history (
                student_id, model_name, predicted_outcome,
                pass_probability, fail_probability, risk_category,
                interventions_json, predicted_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                str(sid).strip().upper(),
                model_name,
                pred,
                round(pass_prob, 4),
                round(fail_prob, 4),
                risk_category,
                json.dumps(interventions),
                actor_username
            ))
            conn.commit()
            result["history_id"] = cursor.lastrowid
        except Exception as e:
            logger.warning(f"Could not persist prediction history: {e}")
        finally:
            if close_conn:
                conn.close()

    return result


def get_prediction_history(student_id: str = None, limit: int = 50, conn = None) -> list[dict]:
    """Fetches recent prediction history, optionally filtered by student_id."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        if student_id:
            cursor.execute("""
            SELECT id, student_id, model_name, predicted_outcome, pass_probability,
                   fail_probability, risk_category, interventions_json, predicted_by, created_at
            FROM prediction_history
            WHERE student_id = ?
            ORDER BY created_at DESC
            LIMIT ?;
            """, (student_id.strip().upper(), limit))
        else:
            cursor.execute("""
            SELECT id, student_id, model_name, predicted_outcome, pass_probability,
                   fail_probability, risk_category, interventions_json, predicted_by, created_at
            FROM prediction_history
            ORDER BY created_at DESC
            LIMIT ?;
            """, (limit,))

        rows = cursor.fetchall()
        history = []
        for r in rows:
            d = dict(r)
            try:
                d["interventions"] = json.loads(d["interventions_json"])
            except Exception:
                d["interventions"] = []
            d["outcome_label"] = "Pass" if d["predicted_outcome"] == 1 else "Fail"
            d["pass_probability_pct"] = round(d["pass_probability"] * 100, 1)
            history.append(d)
        return history
    finally:
        if close_conn:
            conn.close()


def run_batch_screening(
    df: pd.DataFrame,
    model_name: str = "Logistic Regression",
    actor_username: str = "system",
    save_to_db: bool = False,
    conn = None
) -> tuple[pd.DataFrame, list[str]]:
    """
    Screens an entire DataFrame of student records.
    Validates required columns, produces pass probability and risk categorization.
    Returns (result_df, validation_errors).
    """
    errors = []

    # Check for missing feature columns
    missing_cols = [c for c in FEATURE_COLS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required feature columns: {', '.join(missing_cols)}")
        return pd.DataFrame(), errors

    preprocessors, models = load_artifacts()
    if model_name not in models:
        errors.append(f"Model '{model_name}' is not recognized.")
        return pd.DataFrame(), errors

    model = models[model_name]
    imputer = preprocessors['imputer']
    scaler = preprocessors['scaler']

    # Copy features
    features_df = df[FEATURE_COLS].copy()

    # Numeric coercion
    for col in FEATURE_COLS:
        features_df[col] = pd.to_numeric(features_df[col], errors='coerce')

    try:
        imputed_arr = imputer.transform(features_df)
        scaled_arr = scaler.transform(imputed_arr)

        preds = model.predict(scaled_arr)
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba(scaled_arr)[:, 1]
        else:
            probs = np.array([1.0 if p == 1 else 0.0 for p in preds])

        output_df = df.copy()
        output_df['Predicted_Outcome'] = ['Pass' if p == 1 else 'Fail' for p in preds]
        output_df['Pass_Probability (%)'] = np.round(probs * 100, 1)
        output_df['Risk_Level'] = [
            determine_risk_category(p) for p in probs
        ]

        return output_df, errors
    except Exception as e:
        errors.append(f"Inference error during batch screening: {e}")
        return pd.DataFrame(), errors
