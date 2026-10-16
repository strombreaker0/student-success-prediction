"""
Login and Registration View.
Includes safe first-time administrator initialization when no admin exists.
"""

import streamlit as st
from src.services.auth_service import (
    authenticate_user, register_user, has_admin_user,
    create_session, validate_password_strength
)
from src.ui.components import render_header


def render_login_view():
    """Renders the authentication portal."""
    render_header()

    admin_exists = has_admin_user()

    col_l, col_center, col_r = st.columns([1, 2, 1])

    with col_center:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #0f172a; margin-bottom: 4px;">Institutional Access Portal</h2>
            <p style="color: #64748b; font-size: 14px;">Sign in with your institutional credentials to access academic analytics.</p>
        </div>
        """, unsafe_allow_html=True)

        if not admin_exists:
            tabs = st.tabs(["First-Time Setup", "Sign In", "Register Account"])
            with tabs[0]:
                st.warning("No administrator account detected. Please configure the initial administrator.")
                with st.form("admin_setup_form"):
                    adm_name = st.text_input("Administrator Full Name", placeholder="e.g. Head of Department")
                    adm_user = st.text_input("Admin Username", placeholder="e.g. admin")
                    adm_email = st.text_input("Admin Email Address", placeholder="e.g. admin@institution.edu")
                    adm_pwd = st.text_input("Admin Password (min 8 chars, 1 digit, 1 letter)", type="password")
                    adm_pwd2 = st.text_input("Confirm Password", type="password")
                    btn_adm = st.form_submit_button("Initialize Administrator Account", use_container_width=True)

                    if btn_adm:
                        if adm_pwd != adm_pwd2:
                            st.error("Passwords do not match.")
                        else:
                            ok, msg, u = register_user(
                                username=adm_user,
                                email=adm_email,
                                password=adm_pwd,
                                role="admin",
                                full_name=adm_name
                            )
                            if ok:
                                st.success("Administrator account established! Please switch to 'Sign In'.")
                                st.rerun()
                            else:
                                st.error(msg)
            tab_login = tabs[1]
            tab_register = tabs[2]
        else:
            tabs = st.tabs(["Sign In", "Register New Account"])
            tab_login = tabs[0]
            tab_register = tabs[1]

        # Login Tab
        with tab_login:
            with st.form("login_form"):
                login_id = st.text_input("Username or Email Address")
                login_pwd = st.text_input("Password", type="password")
                btn_login = st.form_submit_button("Sign In", use_container_width=True)

                if btn_login:
                    ok, msg, user = authenticate_user(login_id, login_pwd)
                    if ok:
                        st.session_state.auth_session = create_session(user)
                        st.success(f"Welcome back, {user['full_name']}!")
                        st.rerun()
                    else:
                        st.error(msg)

        # Register Tab
        with tab_register:
            with st.form("register_form"):
                reg_name = st.text_input("Full Name", placeholder="e.g. Dr. Jane Smith or John Doe")
                reg_user = st.text_input("Username (alphanumeric, 3-30 chars)", placeholder="e.g. janesmith")
                reg_email = st.text_input("Email Address", placeholder="e.g. janesmith@institution.edu")

                reg_role = st.selectbox(
                    "Account Role",
                    options=["faculty", "student"],
                    format_func=lambda r: "Faculty / Academic Advisor" if r == "faculty" else "Student (View Own Records Only)"
                )

                linked_sid = ""
                if reg_role == "student":
                    linked_sid = st.text_input("Student ID (e.g. STU_1000)", help="Must match an existing student record in the institution database.")

                reg_pwd = st.text_input("Password (min 8 chars, 1 letter, 1 digit)", type="password")
                reg_pwd2 = st.text_input("Confirm Password", type="password")

                btn_reg = st.form_submit_button("Register Account", use_container_width=True)

                if btn_reg:
                    if reg_pwd != reg_pwd2:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg, created_user = register_user(
                            username=reg_user,
                            email=reg_email,
                            password=reg_pwd,
                            role=reg_role,
                            full_name=reg_name,
                            linked_student_id=linked_sid if reg_role == "student" else None
                        )
                        if ok:
                            st.success("Registration complete! You may now sign in using your credentials.")
                        else:
                            st.error(msg)
