"""
Batch Student Screening View.
Performs cohort-wide risk screening, validates CSV upload schemas,
identifies at-risk learners, and exports actionable intervention rosters.
"""

import streamlit as st
import pandas as pd
from src.services.prediction_service import (
    run_batch_screening, get_available_models, FEATURE_COLS
)
from src.services.student_service import list_students


def render_batch_screening_view(user: dict):
    st.subheader("Cohort-Wide Batch Student Screening")
    st.write("Upload a class CSV roster or screen a sample student cohort to identify all at-risk learners at once.")

    # Model selector
    model_options = get_available_models()
    selected_model = st.selectbox("Select Classification Algorithm for Screening", options=model_options, index=0)

    # File Uploader
    uploaded_file = st.file_uploader(
        "Upload Class Roster CSV",
        type=['csv'],
        help=f"CSV file must include the following feature columns: {', '.join(FEATURE_COLS)}"
    )

    batch_df = None

    if uploaded_file is not None:
        try:
            batch_df = pd.read_csv(uploaded_file)
            st.success(f"Uploaded CSV with {len(batch_df)} rows and {len(batch_df.columns)} columns.")
        except Exception as e:
            st.error(f"Failed to parse uploaded CSV: {e}")
            return
    else:
        st.info("No file uploaded. Screening a sample cohort of 20 students from database:")
        students, _ = list_students(limit=20)
        if students:
            batch_df = pd.DataFrame(students)
        else:
            st.warning("No records found in database to sample.")
            return

    # Schema Validation
    missing_cols = [c for c in FEATURE_COLS if c not in batch_df.columns]
    if missing_cols:
        st.error(f"❌ Schema Validation Failed! The uploaded CSV is missing {len(missing_cols)} required columns:")
        for mc in missing_cols:
            st.markdown(f"- `{mc}`")
        st.info(f"Required schema features: `{', '.join(FEATURE_COLS)}`")
        return

    # Execute Batch Screening
    with st.spinner(f"Screening {len(batch_df)} students using {selected_model}..."):
        result_df, errors = run_batch_screening(
            df=batch_df,
            model_name=selected_model,
            actor_username=user.get("username", "evaluator")
        )

    if errors:
        for err in errors:
            st.error(err)
        return

    # Screened Summary Metrics
    total_screened = len(result_df)
    at_risk_count = (result_df['Predicted_Outcome'] == 'Fail').sum()
    safe_count = total_screened - at_risk_count
    risk_rate = (at_risk_count / total_screened * 100) if total_screened > 0 else 0.0

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Total Students Screened", f"{total_screened:,}")
    m_col2.metric("Safe / Passing Students", f"{safe_count:,}")
    m_col3.metric(
        "At-Risk Students Identified",
        f"{at_risk_count:,}",
        delta=f"-{risk_rate:.1f}% At-Risk",
        delta_color="inverse"
    )

    st.markdown("---")
    st.markdown("#### Screened Cohort Risk Stratification")

    # Filter by risk tier in the view
    risk_filter = st.selectbox(
        "Filter Screened Table by Risk Level",
        options=["All Students", "High Risk (At-Risk)", "Moderate Risk", "Low Risk"]
    )

    filtered_df = result_df.copy()
    if risk_filter != "All Students":
        filtered_df = filtered_df[filtered_df['Risk_Level'] == risk_filter]

    def highlight_risk_level(val):
        if val == 'High Risk':
            return 'background-color: #fef2f2; color: #dc2626; font-weight: 700;'
        elif val == 'Moderate Risk':
            return 'background-color: #fffbeb; color: #d97706;'
        return 'background-color: #ecfdf5; color: #059669;'

    # Display columns
    cols_to_show = ['student_id', 'attendance_rate', 'study_hours_per_week', 'previous_scores', 'Predicted_Outcome', 'Pass_Probability (%)', 'Risk_Level']
    avail_cols = [c for c in cols_to_show if c in filtered_df.columns]

    st.dataframe(
        filtered_df[avail_cols].style.map(highlight_risk_level, subset=['Risk_Level']),
        use_container_width=True
    )

    # Download Screened Report
    csv_bytes = result_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Screened Intervention Roster (CSV)",
        data=csv_bytes,
        file_name="student_intervention_screening_report.csv",
        mime="text/csv",
        use_container_width=True
    )
