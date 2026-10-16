"""
Student Management View.
Provides full CRUD capabilities, searching, filtering, validation, and CSV export.
"""

import streamlit as st
import pandas as pd
from src.services.student_service import (
    list_students, add_student, update_student, delete_student,
    get_student_by_id, export_students_to_csv
)
from src.services.auth_service import can_manage_students, can_delete_student


def render_student_management_view(user: dict):
    st.subheader("Student Roster Management")
    st.write("Browse, search, add, edit, and export student academic and behavioral profiles.")

    user_can_manage = can_manage_students(user)
    user_can_delete = can_delete_student(user)

    # Tabs for Roster View vs Add Student
    if user_can_manage:
        tabs = st.tabs(["Student Directory", "Add New Student Record"])
        tab_list = tabs[0]
        tab_add = tabs[1]
    else:
        tab_list = st.container()
        tab_add = None

    # ---------------- TAB 1: LIST / SEARCH / ACTIONS ----------------
    with tab_list:
        # Search & Filter Row
        col_search, col_filter, col_export = st.columns([2, 1.5, 1])

        with col_search:
            search_query = st.text_input("Search Student ID", placeholder="e.g. STU_1001", key="stu_search_q")

        with col_filter:
            outcome_filter = st.selectbox(
                "Filter Outcome",
                options=["All", "Passed", "Failed", "Pending / Unrecorded"],
                key="stu_outcome_f"
            )

        with col_export:
            st.write("")
            st.write("")
            csv_export = export_students_to_csv(
                search_query=search_query,
                outcome_filter=outcome_filter,
                requesting_user=user
            )
            st.download_button(
                label="📥 Export CSV",
                data=csv_export,
                file_name="student_records_export.csv",
                mime="text/csv",
                disabled=not bool(csv_export),
                use_container_width=True
            )

        # Pagination & Retrieval
        students, total_count = list_students(
            search_query=search_query,
            outcome_filter=outcome_filter,
            requesting_user=user,
            limit=250,
            offset=0
        )

        st.caption(f"Showing {len(students)} of {total_count} matching student records.")

        if not students:
            st.info("No student records match the search and filter criteria.")
        else:
            # Display Table
            df = pd.DataFrame(students)
            display_cols = [
                'student_id', 'attendance_rate', 'study_hours_per_week',
                'previous_scores', 'assignment_completion_rate', 'tutoring_sessions',
                'sleep_hours', 'extracurricular', 'internet_access', 'passed'
            ]
            clean_df = df[[c for c in display_cols if c in df.columns]].copy()
            clean_df['passed'] = clean_df['passed'].map({1: 'Pass', 0: 'Fail', None: 'Pending'})
            clean_df['extracurricular'] = clean_df['extracurricular'].map({1: 'Yes', 0: 'No'})
            clean_df['internet_access'] = clean_df['internet_access'].map({1: 'Yes', 0: 'No'})

            st.dataframe(clean_df, use_container_width=True)

            # Record Inspection & Operations
            st.markdown("---")
            st.markdown("#### Individual Student Operations")

            selected_sid = st.selectbox(
                "Select a Student ID to View, Edit, or Predict",
                options=[s["student_id"] for s in students],
                key="select_student_op"
            )

            if selected_sid:
                student_data = get_student_by_id(selected_sid, requesting_user=user)
                if not student_data:
                    st.error("Could not retrieve student details.")
                    return

                col_actions = st.columns([1, 1, 1])

                with col_actions[0]:
                    if st.button("🔍 Open Profile & ML Risk Analysis", use_container_width=True, key=f"btn_prof_{selected_sid}"):
                        st.session_state.active_student_id = selected_sid
                        st.session_state.current_page = "Student Profile & ML Prediction"
                        st.rerun()

                # Edit Student Section (if authorized)
                if user_can_manage:
                    with st.expander(f"✏️ Edit Record: {selected_sid}"):
                        with st.form(f"edit_form_{selected_sid}"):
                            e_col1, e_col2 = st.columns(2)
                            with e_col1:
                                e_att = st.number_input("Attendance Rate (%)", min_value=0.0, max_value=100.0, value=float(student_data["attendance_rate"] or 75.0), step=0.5)
                                e_study = st.number_input("Study Hours / Week", min_value=0.0, max_value=100.0, value=float(student_data["study_hours_per_week"] or 14.0), step=0.5)
                                e_prev = st.number_input("Previous Scores (%)", min_value=0.0, max_value=100.0, value=float(student_data["previous_scores"] or 65.0), step=0.5)
                                e_assign = st.number_input("Assignment Completion (%)", min_value=0.0, max_value=100.0, value=float(student_data["assignment_completion_rate"] or 80.0), step=0.5)
                                e_tutor = st.number_input("Tutoring Sessions", min_value=0, max_value=50, value=int(student_data["tutoring_sessions"] or 2), step=1)
                            with e_col2:
                                e_sleep = st.number_input("Sleep Hours / Night", min_value=0.0, max_value=24.0, value=float(student_data["sleep_hours"] or 7.0), step=0.5)
                                e_extra = st.selectbox("Extracurricular", options=[1, 0], index=0 if student_data["extracurricular"] == 1 else 1, format_func=lambda x: "Yes" if x == 1 else "No")
                                e_net = st.selectbox("Internet Access", options=[1, 0], index=0 if student_data["internet_access"] == 1 else 1, format_func=lambda x: "Yes" if x == 1 else "No")
                                e_exam = st.number_input("Final Exam Score (%) (Optional)", min_value=0.0, max_value=100.0, value=float(student_data["final_exam_score"]) if student_data["final_exam_score"] is not None else 0.0)
                                e_passed = st.selectbox("Historical Passed Status", options=[1, 0, None], index=0 if student_data["passed"] == 1 else (1 if student_data["passed"] == 0 else 2), format_func=lambda x: "Passed (1)" if x == 1 else ("Failed (0)" if x == 0 else "Pending / None"))

                            btn_update = st.form_submit_button("Save Changes", use_container_width=True)

                            if btn_update:
                                update_payload = {
                                    "attendance_rate": e_att,
                                    "study_hours_per_week": e_study,
                                    "previous_scores": e_prev,
                                    "assignment_completion_rate": e_assign,
                                    "tutoring_sessions": e_tutor,
                                    "sleep_hours": e_sleep,
                                    "extracurricular": e_extra,
                                    "internet_access": e_net,
                                    "final_exam_score": e_exam if e_exam > 0 else None,
                                    "passed": e_passed
                                }
                                ok, msg, _ = update_student(selected_sid, update_payload, requesting_user=user)
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

                # Delete Student Section (Admin only)
                if user_can_delete:
                    with st.expander(f"🗑️ Delete Record: {selected_sid} (Admin Only)"):
                        st.warning(f"Are you sure you want to delete student {selected_sid}? This will also delete associated prediction records.")
                        confirm_del = st.checkbox(f"Yes, permanently delete {selected_sid}", key=f"del_chk_{selected_sid}")
                        if st.button("Confirm Delete", type="primary", disabled=not confirm_del, key=f"del_btn_{selected_sid}"):
                            ok, msg = delete_student(selected_sid, requesting_user=user)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

    # ---------------- TAB 2: ADD NEW STUDENT ----------------
    if tab_add is not None:
        with tab_add:
            st.markdown("#### Register New Student Record")
            with st.form("add_student_form"):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    new_id = st.text_input("Student ID (Unique)", placeholder="e.g. STU_2201").strip().upper()
                    new_att = st.number_input("Attendance Rate (%)", min_value=0.0, max_value=100.0, value=75.0, step=0.5)
                    new_study = st.number_input("Weekly Study Hours (hrs/wk)", min_value=0.0, max_value=100.0, value=14.0, step=0.5)
                    new_prev = st.number_input("Previous Examination Score (%)", min_value=0.0, max_value=100.0, value=65.0, step=0.5)
                    new_assign = st.number_input("Assignment Completion Rate (%)", min_value=0.0, max_value=100.0, value=80.0, step=0.5)
                with col_a2:
                    new_tutor = st.number_input("Tutoring Sessions Attended", min_value=0, max_value=50, value=2, step=1)
                    new_sleep = st.number_input("Average Sleep Hours / Night", min_value=0.0, max_value=24.0, value=7.0, step=0.5)
                    new_extra = st.selectbox("Extracurricular Participation", options=[1, 0], format_func=lambda x: "Yes" if x == 1 else "No")
                    new_net = st.selectbox("High-Speed Internet Access", options=[1, 0], format_func=lambda x: "Yes" if x == 1 else "No")
                    new_exam = st.number_input("Final Exam Score (%) (Optional)", min_value=0.0, max_value=100.0, value=0.0)
                    new_passed = st.selectbox("Historical Outcome (Optional)", options=[None, 1, 0], format_func=lambda x: "Pending / Unrecorded" if x is None else ("Passed" if x == 1 else "Failed"))

                btn_add = st.form_submit_button("Add Student to Roster", use_container_width=True)

                if btn_add:
                    payload = {
                        "student_id": new_id,
                        "attendance_rate": new_att,
                        "study_hours_per_week": new_study,
                        "previous_scores": new_prev,
                        "assignment_completion_rate": new_assign,
                        "tutoring_sessions": new_tutor,
                        "sleep_hours": new_sleep,
                        "extracurricular": new_extra,
                        "internet_access": new_net,
                        "final_exam_score": new_exam if new_exam > 0 else None,
                        "passed": new_passed
                    }
                    ok, msg, created = add_student(payload, requesting_user=user)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
