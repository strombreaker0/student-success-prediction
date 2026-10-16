"""
Student Profile, ML Prediction, and Four-Year Academic History Management View.
Allows faculty and administrators to view behavioral indicators, run ML predictions,
manage 4-year semester results, add subject grades, record achievements,
and download student academic transcripts.
"""

import streamlit as st
import pandas as pd
from src.services.student_service import get_student_by_id
from src.services.prediction_service import (
    predict_student, get_prediction_history, get_available_models
)
from src.services.academic_history_service import (
    get_student_academic_history, upsert_semester_record,
    add_subject_result, delete_subject_result,
    add_student_activity, delete_student_activity,
    export_academic_transcript_csv, generate_academic_transcript_pdf,
    VALID_SEMESTER_STATUSES, VALID_ACTIVITY_TYPES
)
from src.services.auth_service import can_run_predictions, can_view_student, can_manage_students
from src.ui.components import render_risk_result, render_interventions_box


def render_student_profile_view(user: dict):
    st.subheader("Student Academic Profile & Four-Year Progress Management")
    st.write("Comprehensive academic records, four-year semester history, and supervised ML decision-support.")

    # Determine Student ID
    target_sid = st.session_state.get("active_student_id")

    # If student role, force their own student ID
    if user.get("role") == "student":
        target_sid = user.get("linked_student_id")

    if not target_sid:
        target_sid = st.text_input("Enter Student ID to inspect:", placeholder="e.g. STU_1000").strip().upper()

    if not target_sid:
        st.info("Please enter or select a Student ID from the Student Directory.")
        return

    # Security check: Can user view this student?
    if not can_view_student(user, target_sid):
        st.error(f"Unauthorized: You do not have permission to view profile '{target_sid}'.")
        return

    student = get_student_by_id(target_sid, requesting_user=user)
    if not student:
        st.error(f"Student record '{target_sid}' not found.")
        return

    user_can_manage = can_manage_students(user)

    # 1. Base Student Header Card
    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-header">
            <h3>Student ID: {student['student_id']}</h3>
            <span style="color: #64748b; font-size: 13px;">Last updated: {student.get('updated_at', 'N/A')}</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            <div><b>Attendance Rate:</b> {student['attendance_rate'] or 'N/A'}%</div>
            <div><b>Weekly Study Hours:</b> {student['study_hours_per_week'] or 'N/A'} hrs</div>
            <div><b>Prior Exam Score:</b> {student['previous_scores'] or 'N/A'}%</div>
            <div><b>Assignment Rate:</b> {student['assignment_completion_rate'] or 'N/A'}%</div>
            <div><b>Tutoring Sessions:</b> {student['tutoring_sessions'] if student['tutoring_sessions'] is not None else 'N/A'}</div>
            <div><b>Sleep Hours / Night:</b> {student['sleep_hours'] or 'N/A'} hrs</div>
            <div><b>Extracurriculars:</b> {'Yes' if student['extracurricular'] == 1 else 'No'}</div>
            <div><b>Internet Access:</b> {'Yes' if student['internet_access'] == 1 else 'No'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Transcript Download Row
    t_col1, t_col2, _ = st.columns([1.5, 1.5, 4])
    with t_col1:
        pdf_bytes = generate_academic_transcript_pdf(target_sid, requesting_user=user)
        st.download_button(
            label="📄 Download Transcript (PDF)",
            data=pdf_bytes,
            file_name=f"{target_sid}_transcript.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with t_col2:
        csv_str = export_academic_transcript_csv(target_sid, requesting_user=user)
        st.download_button(
            label="📊 Export Transcript (CSV)",
            data=csv_str.encode('utf-8'),
            file_name=f"{target_sid}_transcript.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.write("")

    # View Tabs
    profile_tabs = st.tabs([
        "🎯 Supervised ML Risk Prediction",
        "📅 Four-Year Progress & Grade Cards",
        "✏️ Record Semester & Subject Results",
        "🏆 Record Activities & Achievements"
    ])

    # ---------------- TAB 1: ML PREDICTION & AUDIT TRAIL ----------------
    with profile_tabs[0]:
        st.markdown("#### 📜 Historical Term-End Outcome")
        exam_score = student.get('final_exam_score')
        passed_stat = student.get('passed')
        h_col1, h_col2 = st.columns(2)
        with h_col1:
            if exam_score is not None:
                st.metric("Recorded Final Exam Score", f"{exam_score:.1f}%")
            else:
                st.info("Recorded Final Exam Score: Pending / Not Yet Taken")
        with h_col2:
            if passed_stat == 1:
                st.success("Historical Examination Status: PASSED")
            elif passed_stat == 0:
                st.error("Historical Examination Status: FAILED")
            else:
                st.info("Historical Examination Status: In Progress")

        st.markdown("---")
        st.markdown("#### 🤖 Supervised ML Predictive Assessment")
        st.caption("Predictive models evaluate daily behavioral metrics. Final exam marks and pass status are NOT input features.")

        if can_run_predictions(user):
            model_options = get_available_models()
            sel_col1, sel_col2 = st.columns([2, 1])
            with sel_col1:
                selected_model = st.selectbox("Select Predictive Model", options=model_options, index=0)
            with sel_col2:
                st.write("")
                st.write("")
                run_btn = st.button("Run Model Prediction", type="primary", use_container_width=True)

            if run_btn:
                with st.spinner("Processing preprocessors & running model inference..."):
                    try:
                        pred_res = predict_student(
                            student_data=student,
                            model_name=selected_model,
                            actor_username=user.get('username', 'faculty'),
                            save_history=True
                        )
                        st.session_state[f"last_pred_{target_sid}"] = pred_res
                        st.success("Prediction executed and recorded to institutional audit log.")
                    except Exception as e:
                        st.error(f"Inference error: {e}")

            active_pred = st.session_state.get(f"last_pred_{target_sid}")
            if active_pred:
                st.write("")
                render_risk_result(active_pred)
                st.write("")
                render_interventions_box(active_pred.get("interventions", []))

        st.markdown("---")
        st.markdown("#### Institutional Prediction History for this Student")
        history = get_prediction_history(student_id=target_sid, limit=20)
        if history:
            h_df = pd.DataFrame(history)
            disp_df = h_df[['created_at', 'model_name', 'outcome_label', 'pass_probability_pct', 'risk_category', 'predicted_by']].copy()
            disp_df.columns = ['Timestamp', 'Model', 'Predicted Outcome', 'Pass Prob (%)', 'Risk Tier', 'Evaluator']
            st.dataframe(disp_df, use_container_width=True)
        else:
            st.caption("No prior predictions logged for this student.")

    # ---------------- TAB 2: FOUR-YEAR PROGRESS & GRADE CARDS ----------------
    with profile_tabs[1]:
        st.markdown("#### Complete Four-Year Academic Journey")
        st.write("Review all semesters (1 through 8), subject marks, internal assessments, and earned credits.")

        acad_history = get_student_academic_history(target_sid, requesting_user=user)
        if acad_history:
            analytics = acad_history["analytics"]
            c_row1, c_row2, c_row3, c_row4 = st.columns(4)
            c_row1.metric("Cumulative CGPA", f"{analytics['overall_cgpa']:.2f}" if analytics['overall_cgpa'] is not None else "N/A")
            c_row2.metric("Semesters Completed", f"{analytics['completed_semesters_count']} of 8")
            c_row3.metric("Credits Earned", f"{analytics['total_credits_earned']:.0f}")
            c_row4.metric("Avg Attendance", f"{analytics['overall_attendance']:.1f}%" if analytics['overall_attendance'] is not None else "N/A")

            st.write("")

            for yr in acad_history["years"]:
                cgpa_label = f"CGPA: {yr['cgpa']:.2f}" if yr.get("cgpa") is not None else "CGPA: Pending"
                with st.expander(f"📚 {yr['year_name']} — Status: {yr['status']} ({cgpa_label})", expanded=False):
                    for sem in yr["semesters"]:
                        sem_num = sem["semester_number"]
                        st.markdown(f"**Semester {sem_num}** ({sem['status']}) — SGPA: {sem['sgpa'] if sem['sgpa'] is not None else 'N/A'} | Credits: {sem['credits_earned']}/{sem['total_credits']} | Attendance: {sem['attendance_rate'] or 'N/A'}%")

                        subjs = sem.get("subjects", [])
                        if not subjs:
                            st.caption("No individual subject records entered for this semester.")
                        else:
                            s_df = pd.DataFrame(subjs)[['subject_code', 'subject_name', 'credits', 'internal_marks', 'external_marks', 'total_marks', 'grade', 'status']]
                            s_df.columns = ['Code', 'Subject', 'Credits', 'Internal (20)', 'External (80)', 'Total (100)', 'Grade', 'Status']
                            st.dataframe(s_df, use_container_width=True, hide_index=True)
                        st.markdown("---")

    # ---------------- TAB 3: RECORD SEMESTER & SUBJECTS ----------------
    with profile_tabs[2]:
        if not user_can_manage:
            st.info("Entering or modifying semester records requires Faculty or Administrator credentials.")
        else:
            st.markdown("#### Enter or Update Semester Results")
            st.write("Specify semester-level SGPA, credits, attendance percentage, and status.")

            with st.form(f"sem_form_{target_sid}"):
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    sem_num_inp = st.selectbox("Select Semester", options=list(range(1, 9)), format_func=lambda x: f"Semester {x} (Year {(x+1)//2})")
                    sem_stat_inp = st.selectbox("Semester Status", options=VALID_SEMESTER_STATUSES, index=0)
                    sem_sgpa_inp = st.number_input("Semester SGPA (0.00 to 10.00)", min_value=0.0, max_value=10.0, value=7.50, step=0.05)
                    sem_tot_cred = st.number_input("Total Credits Attempted", min_value=0.0, max_value=40.0, value=20.0, step=1.0)
                with col_s2:
                    sem_earn_cred = st.number_input("Credits Earned", min_value=0.0, max_value=40.0, value=20.0, step=1.0)
                    sem_att_inp = st.number_input("Semester Attendance Rate (%)", min_value=0.0, max_value=100.0, value=85.0, step=0.5)
                    sem_ass_inp = st.number_input("Coursework / Assignment Rate (%)", min_value=0.0, max_value=100.0, value=85.0, step=0.5)
                    sem_rem_inp = st.text_input("Remarks / Mentor Notes", placeholder="e.g. Cleared all core theory papers on first attempt.")

                btn_save_sem = st.form_submit_button("Save Semester Record", use_container_width=True)

                if btn_save_sem:
                    ok, msg, _ = upsert_semester_record(
                        student_id=target_sid,
                        semester_number=sem_num_inp,
                        status=sem_stat_inp,
                        sgpa=sem_sgpa_inp,
                        total_credits=sem_tot_cred,
                        credits_earned=sem_earn_cred,
                        attendance_rate=sem_att_inp,
                        assignment_rate=sem_ass_inp,
                        remarks=sem_rem_inp,
                        requesting_user=user
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            st.markdown("---")
            st.markdown("#### Add Subject Grade to Semester")
            st.write("Add course-level marks, grades, and credits to a chosen semester.")

            with st.form(f"subj_form_{target_sid}"):
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    sub_sem_target = st.selectbox("Semester for Subject", options=list(range(1, 9)), format_func=lambda x: f"Semester {x}")
                    sub_code = st.text_input("Subject Code (Unique per semester)", placeholder="e.g. CS201").strip().upper()
                    sub_name = st.text_input("Subject Title", placeholder="e.g. Data Structures & Algorithms")
                    sub_cred = st.number_input("Subject Credits", min_value=1.0, max_value=8.0, value=4.0, step=0.5)
                with col_sub2:
                    sub_int = st.number_input("Internal Assessment Marks (0-20)", min_value=0.0, max_value=100.0, value=18.0, step=1.0)
                    sub_ext = st.number_input("Semester End Exam Marks (0-80)", min_value=0.0, max_value=100.0, value=62.0, step=1.0)
                    sub_tot = st.number_input("Total Marks (0-100)", min_value=0.0, max_value=100.0, value=80.0, step=1.0)
                    sub_grade = st.selectbox("Grade", options=["O", "A+", "A", "B+", "B", "C", "P", "F"], index=2)

                btn_add_subj = st.form_submit_button("Record Subject Grade", use_container_width=True)

                if btn_add_subj:
                    ok_sub, msg_sub, _ = add_subject_result(
                        student_id=target_sid,
                        semester_number=sub_sem_target,
                        subject_code=sub_code,
                        subject_name=sub_name,
                        credits=sub_cred,
                        internal_marks=sub_int,
                        external_marks=sub_ext,
                        total_marks=sub_tot,
                        grade=sub_grade,
                        status="Pass" if sub_grade != "F" else "Fail",
                        requesting_user=user
                    )
                    if ok_sub:
                        st.success(msg_sub)
                        st.rerun()
                    else:
                        st.error(msg_sub)

    # ---------------- TAB 4: RECORD ACTIVITIES & ACHIEVEMENTS ----------------
    with profile_tabs[3]:
        if not user_can_manage:
            st.info("Recording co-curricular activities and certificates requires Faculty or Administrator credentials.")
        else:
            st.markdown("#### Record Co-Curricular Project, Certificate or Achievement")
            with st.form(f"act_form_{target_sid}"):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    act_type = st.selectbox("Activity Category", options=VALID_ACTIVITY_TYPES)
                    act_title = st.text_input("Title", placeholder="e.g. Autonomous Robotic Navigation Project")
                    act_org = st.text_input("Organization / Issuer / Venue", placeholder="e.g. IEEE Student Chapter")
                    act_year = st.selectbox("Academic Year", options=[1, 2, 3, 4], format_func=lambda x: f"Year {x}")
                with col_a2:
                    act_date = st.text_input("Date or Duration", placeholder="e.g. Fall 2024 / 8 Weeks")
                    act_award = st.text_input("Outcome / Award / Honor", placeholder="e.g. 1st Place Best Project Award")
                    act_skills = st.text_input("Key Skills Demonstrated", placeholder="e.g. Python, ROS, Computer Vision")
                    act_desc = st.text_area("Detailed Description", placeholder="Summary of responsibilities and achievements...")

                btn_save_act = st.form_submit_button("Save Achievement to Portfolio", use_container_width=True)

                if btn_save_act:
                    ok_act, msg_act, _ = add_student_activity(
                        student_id=target_sid,
                        activity_type=act_type,
                        title=act_title,
                        description=act_desc,
                        organization_or_issuer=act_org,
                        date_or_period=act_date,
                        outcome_or_award=act_award,
                        academic_year=act_year,
                        skills_acquired=act_skills,
                        requesting_user=user
                    )
                    if ok_act:
                        st.success(msg_act)
                        st.rerun()
                    else:
                        st.error(msg_act)
