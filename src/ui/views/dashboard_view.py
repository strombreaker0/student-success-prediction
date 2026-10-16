"""
Executive Dashboard View.
Provides database-derived analytics, cohort performance distributions,
and recent machine learning prediction activity.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from src.services.student_service import get_dashboard_summary_metrics, list_students
from src.services.prediction_service import get_prediction_history
from src.ui.components import render_kpi_card


def render_dashboard_view():
    st.subheader("Executive Academic Analytics Dashboard")
    st.write("Aggregated institutional indicators derived from persistent database records.")

    # 1. Fetch live metrics from SQLite
    try:
        metrics = get_dashboard_summary_metrics()
    except Exception as e:
        st.error(f"Error loading dashboard metrics: {e}")
        return

    # 2. Key Performance Indicators Row 1
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card(
            label="Total Enrolled Students",
            value=f"{metrics['total_students']:,}",
            subtitle="Verified cohort size in database",
            border_color="#1e3a8a"
        )
    with col2:
        render_kpi_card(
            label="Historical Pass Rate",
            value=f"{metrics['pass_rate']}%",
            subtitle=f"{metrics['passed_count']} Passed | {metrics['failed_count']} Failed",
            border_color="#059669" if metrics['pass_rate'] >= 75 else "#d97706"
        )
    with col3:
        render_kpi_card(
            label="Average Attendance Rate",
            value=f"{metrics['avg_attendance']}%",
            subtitle="Institutional minimum: 75%",
            border_color="#2563eb"
        )
    with col4:
        render_kpi_card(
            label="Students Needing Support",
            value=f"{metrics['support_needed_count']:,}",
            subtitle="Attendance < 75% or prior failure",
            border_color="#dc2626"
        )

    # Secondary Metrics Row
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        render_kpi_card(
            label="Avg Study Hours",
            value=f"{metrics['avg_study_hours']} hrs/wk",
            subtitle="Recommended: ≥ 14 hrs/wk",
            border_color="#4f46e5"
        )
    with col_s2:
        render_kpi_card(
            label="Avg Prior Score",
            value=f"{metrics['avg_previous_score']}%",
            subtitle="Historical assessment baseline",
            border_color="#0891b2"
        )
    with col_s3:
        render_kpi_card(
            label="Avg Assignment Rate",
            value=f"{metrics['avg_assignment_completion']}%",
            subtitle="Coursework submission metric",
            border_color="#0d9488"
        )
    with col_s4:
        recent_preds = get_prediction_history(limit=500)
        render_kpi_card(
            label="Model Predictions Run",
            value=f"{len(recent_preds)}",
            subtitle="Logged ML inference records",
            border_color="#7c3aed"
        )

    st.markdown("---")

    # 3. Analytics Visualizations Row
    st.markdown("#### Cohort Performance Distributions")

    # Fetch a sample dataframe from database for plotting
    students, _ = list_students(limit=1500)
    if students:
        df = pd.DataFrame(students)

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("##### Attendance Distribution by Examination Outcome")
            fig, ax = plt.subplots(figsize=(6, 3.8))
            plot_df = df.dropna(subset=['attendance_rate', 'passed']).copy()
            plot_df['Outcome'] = plot_df['passed'].map({1: 'Passed', 0: 'Failed'})

            palette = {'Passed': '#059669', 'Failed': '#dc2626'}
            sns.histplot(
                data=plot_df,
                x='attendance_rate',
                hue='Outcome',
                kde=True,
                palette=palette,
                bins=20,
                ax=ax,
                alpha=0.6
            )
            ax.axvline(75.0, color='#d97706', linestyle='--', linewidth=1.5, label='Min Statutory Threshold (75%)')
            ax.set_xlabel("Attendance Rate (%)", fontsize=10)
            ax.set_ylabel("Student Count", fontsize=10)
            ax.legend(title="Outcome", fontsize=9)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

        with chart_col2:
            st.markdown("##### Study Hours vs Prior Scores")
            fig, ax = plt.subplots(figsize=(6, 3.8))
            plot_df = df.dropna(subset=['study_hours_per_week', 'previous_scores', 'passed']).copy()
            plot_df['Outcome'] = plot_df['passed'].map({1: 'Passed', 0: 'Failed'})

            sns.scatterplot(
                data=plot_df,
                x='study_hours_per_week',
                y='previous_scores',
                hue='Outcome',
                palette={'Passed': '#2563eb', 'Failed': '#ef4444'},
                alpha=0.6,
                ax=ax
            )
            ax.set_xlabel("Weekly Study Hours (hrs)", fontsize=10)
            ax.set_ylabel("Previous Exam Score (%)", fontsize=10)
            ax.legend(title="Outcome", fontsize=9)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

    # 4. Recent Prediction Activity Table
    st.markdown("---")
    st.markdown("#### Recent Model Inference & Risk Screening Activity")
    recent_activity = get_prediction_history(limit=10)

    if recent_activity:
        rec_df = pd.DataFrame(recent_activity)
        display_df = rec_df[['student_id', 'model_name', 'outcome_label', 'pass_probability_pct', 'risk_category', 'predicted_by', 'created_at']].copy()
        display_df.columns = ['Student ID', 'Algorithm', 'Prediction', 'Pass Prob (%)', 'Risk Category', 'Actor', 'Timestamp']

        def highlight_risk(val):
            if val == 'High Risk':
                return 'background-color: #fef2f2; color: #dc2626; font-weight: 600;'
            elif val == 'Moderate Risk':
                return 'background-color: #fffbeb; color: #d97706;'
            return 'background-color: #ecfdf5; color: #059669;'

        st.dataframe(
            display_df.style.map(highlight_risk, subset=['Risk Category']),
            use_container_width=True
        )
    else:
        st.info("No prediction activity recorded yet. Run predictions from the Student Management module or Instant Simulator.")
