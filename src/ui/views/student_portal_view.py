"""
Student Self-Service Four-Year Academic Progress Portal View.
Displays student's 4-year lifecycle (Year 1-4, Semesters 1-8), subject marks,
credits, attendance, interactive progress charts, achievements,
strengths/improvements, ML predictions, and downloadable PDF/CSV transcripts.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.services.academic_history_service import (
    get_student_academic_history, export_academic_transcript_csv,
    generate_academic_transcript_pdf
)
from src.services.prediction_service import get_prediction_history, predict_student
from src.ui.components import render_risk_result, render_interventions_box, render_kpi_card


def render_student_portal_view(user: dict):
    student_id = user.get("linked_student_id")
    if not student_id:
        st.error("No student profile is linked to your user account. Please contact an administrator.")
        return

    # Fetch 4-Year Academic History
    history_data = get_student_academic_history(student_id, requesting_user=user)
    if not history_data:
        st.error(f"Unable to retrieve academic history for Student ID: {student_id}")
        return

    student = history_data["student"]
    analytics = history_data["analytics"]
    years = history_data["years"]
    activities = history_data["activities"]

    # Header and Profile
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; flex-wrap: wrap;">
        <div>
            <h2 style="color: #0f172a; margin: 0 0 4px 0; font-weight: 700;">Student Academic Progress Portal</h2>
            <p style="color: #64748b; font-size: 14px; margin: 0;">Welcome, <b>{user.get('full_name', 'Student')}</b> ({student_id}) | Current Standing: <b>{analytics['current_standing']}</b></p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Transcript Download Buttons Row
    col_dl1, col_dl2, _ = st.columns([1.5, 1.5, 4])
    with col_dl1:
        pdf_bytes = generate_academic_transcript_pdf(student_id, requesting_user=user)
        st.download_button(
            label="📄 Download Official Transcript (PDF)",
            data=pdf_bytes,
            file_name=f"{student_id}_academic_transcript.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_dl2:
        csv_str = export_academic_transcript_csv(student_id, requesting_user=user)
        st.download_button(
            label="📊 Export Academic Records (CSV)",
            data=csv_str.encode('utf-8'),
            file_name=f"{student_id}_academic_records.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.write("")

    # KPI Summary Cards Row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        cgpa_val = f"{analytics['overall_cgpa']:.2f}" if analytics['overall_cgpa'] is not None else "N/A"
        render_kpi_card("Cumulative CGPA", cgpa_val, "Scale: 10.0", "#1e3a8a")
    with k2:
        att_val = f"{analytics['overall_attendance']:.1f}%" if analytics['overall_attendance'] is not None else "N/A"
        render_kpi_card("Cumulative Attendance", att_val, "Institutional Min: 75%", "#059669" if (analytics['overall_attendance'] or 0) >= 75 else "#dc2626")
    with k3:
        credits_val = f"{analytics['total_credits_earned']:.0f}"
        render_kpi_card("Total Credits Earned", credits_val, "Across completed terms", "#2563eb")
    with k4:
        sems_val = f"{analytics['completed_semesters_count']} of 8"
        render_kpi_card("Semesters Completed", sems_val, analytics['current_standing'], "#4f46e5")

    st.markdown("---")

    # Portal Navigation Tabs
    p_tabs = st.tabs([
        "📅 Four-Year Academic Journey",
        "📈 Progress & Analytics Trends",
        "🏆 Projects & Achievements",
        "🎯 Proactive ML Success Evaluation"
    ])

    # ---------------- TAB 1: FOUR-YEAR ACADEMIC JOURNEY ----------------
    with p_tabs[0]:
        st.markdown("#### Four-Year Academic History & Semester Grade Cards")
        st.write("Browse semester-wise performance, subject marks, internal assessments, and earned credits across all 4 years.")

        for yr in years:
            yr_num = yr["academic_year"]
            yr_name = yr["year_name"]
            yr_status = yr["status"]
            yr_cgpa = f"CGPA: {yr['cgpa']:.2f}" if yr.get("cgpa") is not None else "CGPA: Pending"

            with st.expander(f"📚 {yr_name} — Status: {yr_status} ({yr_cgpa})", expanded=(yr_num == 1 or yr_status == "In Progress")):
                st.caption(f"Academic Session: {yr.get('academic_session', 'N/A')} | Remarks: {yr.get('remarks') or 'None'}")

                sem_col1, sem_col2 = st.columns(2)
                semesters = yr["semesters"]

                for i, sem in enumerate(semesters):
                    col = sem_col1 if i % 2 == 0 else sem_col2
                    with col:
                        sem_num = sem["semester_number"]
                        sem_status = sem["status"]
                        sgpa_str = f"SGPA: {sem['sgpa']:.2f}" if sem.get("sgpa") is not None else "SGPA: N/A"

                        st.markdown(f"""
                        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">
                            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px; margin-bottom: 8px;">
                                <h4 style="margin: 0; color: #1e3a8a;">Semester {sem_num}</h4>
                                <span style="font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: {'#ecfdf5; color: #065f46' if sem_status == 'Passed' else ('#fffbeb; color: #92400e' if sem_status == 'In Progress' else '#f1f5f9; color: #64748b')};">
                                    {sem_status}
                                </span>
                            </div>
                            <div style="font-size: 13px; color: #334155; margin-bottom: 8px;">
                                <b>{sgpa_str}</b> &nbsp;|&nbsp; 
                                <b>Credits:</b> {sem['credits_earned']}/{sem['total_credits']} &nbsp;|&nbsp; 
                                <b>Attendance:</b> {sem['attendance_rate'] or 'N/A'}%
                            </div>
                        """, unsafe_allow_html=True)

                        subjects = sem.get("subjects", [])
                        if not subjects:
                            st.caption("No individual subject results entered for this semester yet.")
                        else:
                            subj_df = pd.DataFrame(subjects)[[
                                'subject_code', 'subject_name', 'credits',
                                'internal_marks', 'external_marks', 'total_marks',
                                'grade', 'status'
                            ]].copy()
                            subj_df.columns = ['Code', 'Subject', 'Credits', 'Int (20)', 'Ext (80)', 'Total (100)', 'Grade', 'Result']
                            st.dataframe(subj_df, use_container_width=True, hide_index=True)

                        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- TAB 2: PROGRESS & ANALYTICS TRENDS ----------------
    with p_tabs[1]:
        st.markdown("#### Academic Performance & Indicator Trajectories")
        st.write("Visual progression of your SGPA, attendance discipline, and assignment submission rates across semesters.")

        # Prepare chart dataframe
        chart_records = []
        for sem in history_data["all_semesters"]:
            if sem.get("status") in ("Passed", "Failed", "In Progress") and sem.get("sgpa") is not None:
                chart_records.append({
                    "Semester": f"Sem {sem['semester_number']}",
                    "Sem_Num": sem["semester_number"],
                    "SGPA": sem["sgpa"],
                    "Attendance": sem.get("attendance_rate"),
                    "Assignments": sem.get("assignment_completion_rate"),
                    "Credits_Earned": sem.get("credits_earned", 0.0)
                })

        if not chart_records:
            st.info("Performance charts will display here once semester results (SGPA and Attendance) are recorded by faculty.")
        else:
            cdf = pd.DataFrame(chart_records).sort_values("Sem_Num")

            c_chart1, c_chart2 = st.columns(2)

            with c_chart1:
                st.markdown("##### SGPA Trajectory Across Semesters")
                fig, ax = plt.subplots(figsize=(6.5, 3.8))
                ax.plot(cdf["Semester"], cdf["SGPA"], marker='o', linewidth=2.5, color='#1e3a8a', label='Semester SGPA')
                ax.set_ylim(0.0, 10.0)
                ax.set_ylabel("SGPA (10-Point Scale)", fontsize=10)
                ax.grid(True, linestyle='--', alpha=0.5)
                for x, y in zip(cdf["Semester"], cdf["SGPA"]):
                    ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 7), ha='center', fontsize=9, weight='bold')
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

            with c_chart2:
                st.markdown("##### Attendance & Coursework Rates (%)")
                fig, ax = plt.subplots(figsize=(6.5, 3.8))
                if cdf["Attendance"].notnull().any():
                    ax.plot(cdf["Semester"], cdf["Attendance"], marker='s', linewidth=2, color='#059669', label='Attendance %')
                if cdf["Assignments"].notnull().any():
                    ax.plot(cdf["Semester"], cdf["Assignments"], marker='^', linewidth=2, color='#2563eb', label='Assignments %')
                ax.axhline(75.0, color='#dc2626', linestyle='--', linewidth=1.5, label='Min Attendance (75%)')
                ax.set_ylim(0.0, 105.0)
                ax.set_ylabel("Percentage (%)", fontsize=10)
                ax.grid(True, linestyle='--', alpha=0.5)
                ax.legend(fontsize=8.5, loc='lower right')
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

        st.markdown("---")
        # Strengths & Recommendations Box
        rec_col1, rec_col2 = st.columns(2)
        with rec_col1:
            st.markdown("##### 🌟 Academic Strengths")
            if analytics["strengths"]:
                for s in analytics["strengths"]:
                    st.success(f"✓ {s}")
            else:
                st.caption("Subject strengths will populate as top grades ('O', 'A+') are earned.")

        with rec_col2:
            st.markdown("##### 🎯 Targeted Improvement Areas")
            if analytics["improvement_areas"]:
                for imp in analytics["improvement_areas"]:
                    st.warning(f"⚠️ {imp}")
            else:
                st.success("No critical academic or attendance deficits identified across recorded terms.")

        st.markdown("##### 💡 Strategic Guidance for Next Semester")
        for rec in analytics["recommendations"]:
            st.info(f"ℹ️ {rec}")

    # ---------------- TAB 3: PROJECTS & ACHIEVEMENTS ----------------
    with p_tabs[2]:
        st.markdown("#### Student Portfolio: Projects, Certifications & Achievements")
        st.write("Record of co-curricular engagements, internships, research projects, and certifications.")

        if not activities:
            st.info("No co-curricular activities, certificates, or projects recorded yet. Faculty advisors can add records through Student Management.")
        else:
            for act in activities:
                st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #2563eb; border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <h4 style="margin: 0; color: #0f172a;">{act['title']}</h4>
                        <span style="font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: #eff6ff; color: #1e40af;">
                            {act['activity_type']}
                        </span>
                    </div>
                    <div style="font-size: 13px; color: #475569; margin-bottom: 4px;">
                        <b>Issuer / Organization:</b> {act.get('organization_or_issuer') or 'N/A'} &nbsp;|&nbsp; 
                        <b>Period:</b> {act.get('date_or_period') or 'N/A'} &nbsp;|&nbsp; 
                        <b>Outcome:</b> <span style="color: #059669; font-weight: 600;">{act.get('outcome_or_award') or 'Completed'}</span>
                    </div>
                    <div style="font-size: 13px; color: #334155;">
                        {act.get('description') or ''}
                    </div>
                    {f'<div style="font-size: 12px; color: #64748b; margin-top: 4px;"><b>Skills:</b> {act["skills_acquired"]}</div>' if act.get("skills_acquired") else ''}
                </div>
                """, unsafe_allow_html=True)

    # ---------------- TAB 4: ML SUCCESS EVALUATION ----------------
    with p_tabs[3]:
        st.markdown("#### 🎯 Proactive Machine Learning Success Evaluation")
        st.caption("Supervised machine learning classification evaluating behavioral markers to forecast final exam outcomes.")

        # Show latest logged prediction or generate on-the-fly evaluation
        history_preds = get_prediction_history(student_id=student_id, limit=5)
        if history_preds:
            latest = history_preds[0]
            st.markdown(f"##### Latest Assessment ({latest['created_at'][:10]})")
            render_risk_result(latest)
            st.write("")
            render_interventions_box(latest.get("interventions", []))

            st.markdown("---")
            st.markdown("##### Historical Prediction Log")
            h_df = pd.DataFrame(history_preds)
            disp_df = h_df[['created_at', 'model_name', 'outcome_label', 'pass_probability_pct', 'risk_category', 'predicted_by']].copy()
            disp_df.columns = ['Date', 'Model', 'Predicted Outcome', 'Pass Probability (%)', 'Risk Category', 'Evaluator']
            st.dataframe(disp_df, use_container_width=True, hide_index=True)
        else:
            # Generate advisory evaluation
            eval_res = predict_student(
                student_data=student,
                model_name="Logistic Regression",
                actor_username="student_self_check",
                save_history=False
            )
            render_risk_result(eval_res)
            st.write("")
            render_interventions_box(eval_res.get("interventions", []))
