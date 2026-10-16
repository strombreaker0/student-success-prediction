"""
User Account Management View.
Allows administrators to manage existing user accounts, roles, and access status,
as well as provision new accounts (including student accounts linked to student IDs).
"""

import streamlit as st
import pandas as pd
from src.services.auth_service import (
    list_users, update_user_status, update_user_role,
    register_user, can_manage_users, VALID_ROLES
)


def render_user_management_view(current_user: dict):
    if not can_manage_users(current_user):
        st.error("Access Denied: Administrator role required.")
        return

    st.subheader("Institutional User Administration")
    st.write("Manage staff and student portal accounts, roles, and authentication status.")

    users = list_users()

    tabs = st.tabs(["User Directory & Access Control", "Provision New Account (Admin Only)"])

    # ---------------- TAB 1: DIRECTORY & EDIT ----------------
    with tabs[0]:
        if not users:
            st.info("No registered users found.")
        else:
            # Table of Users
            df = pd.DataFrame(users)
            disp_df = df[['id', 'username', 'email', 'full_name', 'role', 'linked_student_id', 'is_active', 'created_at']].copy()
            disp_df['is_active'] = disp_df['is_active'].map({1: 'Active', 0: 'Disabled'})
            disp_df.columns = ['ID', 'Username', 'Email', 'Full Name', 'Role', 'Linked Student ID', 'Status', 'Created At']

            st.dataframe(disp_df, use_container_width=True)

            st.markdown("---")
            st.markdown("#### Modify Existing User Account")

            user_options = {f"{u['username']} ({u['full_name']} - {u['role']})": u for u in users}
            selected_label = st.selectbox("Select User Account to Modify", options=list(user_options.keys()))

            if selected_label:
                target_u = user_options[selected_label]
                target_uid = target_u['id']

                col_role, col_status = st.columns(2)

                with col_role:
                    st.markdown("##### Update Role")
                    new_role = st.selectbox(
                        "Assign New Role",
                        options=VALID_ROLES,
                        index=VALID_ROLES.index(target_u['role']),
                        key=f"role_sel_{target_uid}"
                    )
                    if st.button("Save New Role", key=f"btn_role_{target_uid}"):
                        ok, msg = update_user_role(target_uid, new_role)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

                with col_status:
                    st.markdown("##### Account Status")
                    current_status = bool(target_u['is_active'])
                    new_status = st.checkbox("Account Enabled (Active)", value=current_status, key=f"status_chk_{target_uid}")

                    if st.button("Update Status", key=f"btn_stat_{target_uid}"):
                        if target_uid == current_user['id'] and not new_status:
                            st.error("Security Protection: You cannot deactivate your own active administrator account.")
                        else:
                            ok, msg = update_user_status(target_uid, 1 if new_status else 0)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

    # ---------------- TAB 2: PROVISION NEW ACCOUNT ----------------
    with tabs[1]:
        st.markdown("#### Provision Institutional User or Student Account")
        st.write("Administrators can directly provision staff, faculty, or student accounts with secure password hashing and database linkage.")

        with st.form("admin_create_user_form"):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                new_full_name = st.text_input("Full Name", placeholder="e.g. Asmita Kumbar")
                new_username = st.text_input("Username (3-30 alphanumeric chars)", placeholder="e.g. stu_asmita")
                new_email = st.text_input("Email Address", placeholder="e.g. student@institution.edu")
            with col_u2:
                new_role = st.selectbox(
                    "User Role",
                    options=["student", "faculty", "admin"],
                    index=0,
                    format_func=lambda r: "Student (Linked to Student ID)" if r == "student" else ("Faculty / Advisor" if r == "faculty" else "System Administrator")
                )
                new_linked_sid = st.text_input(
                    "Linked Student ID",
                    placeholder="e.g. STU_1000",
                    help="Required for Student role. Must correspond to an existing record in the students database."
                )
                new_pwd = st.text_input("Temporary Password (min 8 chars, 1 digit, 1 letter)", type="password")
                new_pwd2 = st.text_input("Confirm Password", type="password")

            btn_provision = st.form_submit_button("Create & Provision Account", use_container_width=True)

            if btn_provision:
                if new_pwd != new_pwd2:
                    st.error("Passwords do not match.")
                elif new_role == "student" and not new_linked_sid.strip():
                    st.error("Student accounts must specify a valid Linked Student ID.")
                else:
                    ok, msg, created = register_user(
                        username=new_username,
                        email=new_email,
                        password=new_pwd,
                        role=new_role,
                        full_name=new_full_name,
                        linked_student_id=new_linked_sid.strip().upper() if new_role == "student" else None
                    )
                    if ok:
                        st.success(f"Account for '{new_username}' successfully created and linked! {msg}")
                        st.rerun()
                    else:
                        st.error(msg)
