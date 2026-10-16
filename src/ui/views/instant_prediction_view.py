"""
Instant Prediction & What-If Scenario Simulator View.
Allows educators to dynamically simulate behavioral parameters and view real-time risk calculations.
"""

import streamlit as st
from src.services.prediction_service import (
    predict_student, get_available_models
)
from src.ui.components import render_risk_result, render_interventions_box


def render_instant_prediction_view(user: dict):
    st.subheader("Instant Scenario Prediction Simulator")
    st.write("Adjust behavioral and academic parameters to simulate potential student trajectories and review recommended interventions.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 📚 Academic Habits & Prior Performance")
        att = st.slider("Attendance Rate (%)", min_value=0.0, max_value=100.0, value=78.0, step=0.5,
                        help="Classroom and lab lecture attendance.")
        study = st.slider("Weekly Study Hours (hrs/wk)", min_value=0.0, max_value=45.0, value=15.0, step=0.5,
                          help="Independent self-study duration outside class.")
        prev = st.slider("Previous Exam Score (%)", min_value=0.0, max_value=100.0, value=65.0, step=1.0,
                         help="Baseline score from previous semester examinations.")
        assign = st.slider("Assignment Completion Rate (%)", min_value=0.0, max_value=100.0, value=85.0, step=1.0,
                           help="Coursework and practical submissions completed on time.")

    with col2:
        st.markdown("##### 🏡 Lifestyle & Remedial Support Factors")
        tutor = st.number_input("Remedial Tutoring Sessions Attended", min_value=0, max_value=20, value=2, step=1,
                                help="Faculty-led doubt-clearing sessions attended.")
        sleep = st.slider("Average Sleep Hours per Night", min_value=3.0, max_value=12.0, value=7.0, step=0.5,
                          help="Nightly rest duration (optimal: 7-8 hours).")
        extra = st.radio("Extracurricular Activity Participation", options=[1, 0], format_func=lambda x: "Yes" if x == 1 else "No", horizontal=True)
        net = st.radio("High-Speed Internet Access at Home", options=[1, 0], format_func=lambda x: "Yes" if x == 1 else "No", horizontal=True)

        model_options = get_available_models()
        selected_model = st.selectbox("Select Supervised ML Classifier", options=model_options, index=0)

    # Input payload
    sim_data = {
        "attendance_rate": att,
        "study_hours_per_week": study,
        "previous_scores": prev,
        "assignment_completion_rate": assign,
        "tutoring_sessions": tutor,
        "sleep_hours": sleep,
        "extracurricular": extra,
        "internet_access": net
    }

    st.divider()

    try:
        # Run inference (do not persist simulated what-if scenarios without student ID)
        pred_res = predict_student(
            student_data=sim_data,
            model_name=selected_model,
            actor_username=user.get("username", "simulator"),
            save_history=False
        )

        col_res1, col_res2 = st.columns([1, 1])

        with col_res1:
            st.markdown("### 🏆 Prediction Outcome")
            render_risk_result(pred_res)

        with col_res2:
            st.markdown("### 💡 Recommended Academic Interventions")
            render_interventions_box(pred_res["interventions"])

    except Exception as e:
        st.error(f"Inference error in simulator: {e}")
