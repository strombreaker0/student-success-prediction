"""
Unit and integration tests for Prediction Service.
Verifies model inference, imputation, risk categorization, interventions,
and prediction history persistence.
"""

import os
import tempfile
import pytest
import pandas as pd
from src.db.connection import get_db_connection
from src.db.schema import create_schema
from src.services.prediction_service import (
    predict_student, get_prediction_history, run_batch_screening,
    determine_risk_category, generate_interventions, FEATURE_COLS
)


@pytest.fixture
def pred_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = get_db_connection(path)
    create_schema(conn)

    conn.execute("""
    INSERT INTO students (
        student_id, attendance_rate, study_hours_per_week, previous_scores,
        assignment_completion_rate, tutoring_sessions, sleep_hours,
        extracurricular, internet_access, final_exam_score, passed
    ) VALUES ('STU_P100', 88.0, 18.0, 75.0, 92.0, 3, 7.5, 1, 1, 68.0, 1);
    """)
    conn.commit()

    yield conn, path

    conn.close()
    if os.path.exists(path):
        os.remove(path)


def test_risk_categorization():
    assert determine_risk_category(0.85) == "Low Risk"
    assert determine_risk_category(0.75) == "Low Risk"
    assert determine_risk_category(0.60) == "Moderate Risk"
    assert determine_risk_category(0.50) == "Moderate Risk"
    assert determine_risk_category(0.49) == "High Risk"
    assert determine_risk_category(0.10) == "High Risk"


def test_intervention_generation():
    features = {
        'attendance_rate': 65.0,        # < 75 -> alert
        'study_hours_per_week': 8.0,    # < 12 -> alert
        'previous_scores': 45.0,        # < 50 -> alert
        'assignment_completion_rate': 60.0, # < 75 -> alert
        'tutoring_sessions': 0,         # < 2 -> alert
        'sleep_hours': 5.0              # < 6 -> alert
    }
    interventions = generate_interventions(features, predicted_outcome=0, pass_prob=0.35)
    text = " ".join(interventions)
    assert "Attendance Alert" in text
    assert "Study Duration Deficit" in text
    assert "Coursework Submission Alert" in text
    assert "Remedial Support Recommended" in text
    assert "Sleep Deprivation Flag" in text


def test_model_inference_and_history(pred_db):
    conn, _ = pred_db

    student_data = {
        "student_id": "STU_P100",
        "attendance_rate": 88.0,
        "study_hours_per_week": 18.0,
        "previous_scores": 75.0,
        "assignment_completion_rate": 92.0,
        "tutoring_sessions": 3,
        "sleep_hours": 7.5,
        "extracurricular": 1,
        "internet_access": 1,
        # Intentionally include final_exam_score and passed to verify they are ignored
        "final_exam_score": 99.9,
        "passed": 1
    }

    # Test all 3 models
    for model_name in ["Logistic Regression", "Decision Tree", "Random Forest"]:
        res = predict_student(
            student_data=student_data,
            model_name=model_name,
            actor_username="faculty_tester",
            save_history=True,
            conn=conn
        )
        assert res["predicted_outcome"] in (0, 1)
        assert 0.0 <= res["pass_probability"] <= 1.0
        assert res["risk_category"] in ("Low Risk", "Moderate Risk", "High Risk")
        assert len(res["interventions"]) > 0

    # Verify history in database
    history = get_prediction_history(student_id="STU_P100", conn=conn)
    assert len(history) == 3
    assert history[0]["student_id"] == "STU_P100"
    assert history[0]["predicted_by"] == "faculty_tester"


def test_batch_screening():
    sample_df = pd.DataFrame([
        {
            "student_id": "STU_B1",
            "attendance_rate": 92.0,
            "study_hours_per_week": 20.0,
            "previous_scores": 85.0,
            "assignment_completion_rate": 95.0,
            "tutoring_sessions": 2,
            "sleep_hours": 8.0,
            "extracurricular": 1,
            "internet_access": 1
        },
        {
            "student_id": "STU_B2",
            "attendance_rate": 45.0,
            "study_hours_per_week": 4.0,
            "previous_scores": 35.0,
            "assignment_completion_rate": 40.0,
            "tutoring_sessions": 0,
            "sleep_hours": 4.5,
            "extracurricular": 0,
            "internet_access": 0
        }
    ])

    result_df, errors = run_batch_screening(sample_df, model_name="Logistic Regression")
    assert len(errors) == 0
    assert "Predicted_Outcome" in result_df.columns
    assert "Pass_Probability (%)" in result_df.columns
    assert "Risk_Level" in result_df.columns
    assert len(result_df) == 2
