"""
Exploratory Data Analysis (EDA) & Feature Insights View.
Displays behavioral correlation patterns, regression trends, and logistic regression odds ratios.
"""

import os
import streamlit as st
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports', 'figures')


def render_eda_view():
    st.subheader("Exploratory Data Analysis (EDA) & Feature Insights")
    st.write("Empirical evidence demonstrating the statistical associations between student behavioral indicators and academic outcomes.")

    col1, col2 = st.columns(2)

    with col1:
        fig1_path = os.path.join(REPORTS_DIR, '1_attendance_vs_outcome.png')
        if os.path.exists(fig1_path):
            st.image(fig1_path, caption="Figure 1: Attendance Distribution by Pass/Fail Outcome", use_container_width=True)

        fig4_path = os.path.join(REPORTS_DIR, '4_feature_coefficients.png')
        if os.path.exists(fig4_path):
            st.image(fig4_path, caption="Figure 3: Logistic Regression Feature Weights (Odds Drivers)", use_container_width=True)

    with col2:
        fig2_path = os.path.join(REPORTS_DIR, '2_study_hours_vs_score.png')
        if os.path.exists(fig2_path):
            st.image(fig2_path, caption="Figure 2: Study Hours vs Final Exam Score Linear Trend", use_container_width=True)

        fig3_path = os.path.join(REPORTS_DIR, '3_correlation_matrix.png')
        if os.path.exists(fig3_path):
            st.image(fig3_path, caption="Figure 4: Inter-Feature Correlation Heatmap", use_container_width=True)

    st.markdown("---")
    st.markdown("#### Feature Coefficient Weights & Odds Ratio Table")
    st.write("""
    The **Odds Ratio ($OR = e^{w_j}$)** quantifies how a one standard deviation increase in each metric impacts the odds of passing the examination:
    - **Weekly Study Hours** ($OR \\approx 1.97$): Each standard deviation increase nearly doubles the odds of passing ($+97\\%$).
    - **Attendance Rate** ($OR \\approx 1.72$): Each standard deviation increase yields a $72\\%$ increase in passing odds.
    """)

    coef_csv = os.path.join(MODELS_DIR, 'logistic_regression_coefficients.csv')
    if os.path.exists(coef_csv):
        coef_table = pd.read_csv(coef_csv)
        st.dataframe(coef_table, use_container_width=True)
    else:
        st.info("Feature coefficient artifact available at `models/logistic_regression_coefficients.csv`.")
