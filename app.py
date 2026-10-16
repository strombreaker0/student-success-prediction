"""
Student Academic Success Prediction System - Main Application Entrypoint
Upgraded Enterprise Educational Analytics Dashboard with SQLite Persistence,
Role-Based Access Control (RBAC), and Supervised Machine Learning Pipelines.

Candidate Credentials:
- Name: Asmita Chandram Kumbar
- Class: SYBSc CS (2nd Year)
- Roll No: SI1161
"""

import streamlit as st
import os

# Page configuration
st.set_page_config(
    page_title="Student Academic Success Prediction System | Educational Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply premium styling
from src.ui.styles import apply_custom_css
st.markdown(apply_custom_css(), unsafe_allow_html=True)

# Database auto-initialization check
from src.db.connection import get_db_connection
from src.db.schema import create_schema
from src.db.migrate import migrate_csv_to_sqlite

@st.cache_resource
def ensure_database_initialized():
    """Ensures database schema exists and initial CSV data is migrated idempotently."""
    conn = get_db_connection()
    try:
        create_schema(conn)
        # Migrate initial student records if empty
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM students;")
        if cursor.fetchone()[0] == 0:
            migrate_csv_to_sqlite(conn=conn)
    finally:
        conn.close()
    return True

ensure_database_initialized()

# Session & Authentication Services
from src.services.auth_service import (
    is_session_expired, refresh_session_activity, DEFAULT_SESSION_TIMEOUT_MINUTES
)
from src.ui.components import render_header
from src.ui.views.login_view import render_login_view
from src.ui.views.dashboard_view import render_dashboard_view
from src.ui.views.student_management_view import render_student_management_view
from src.ui.views.student_profile_view import render_student_profile_view
from src.ui.views.instant_prediction_view import render_instant_prediction_view
from src.ui.views.batch_screening_view import render_batch_screening_view
from src.ui.views.benchmarks_view import render_benchmarks_view
from src.ui.views.eda_view import render_eda_view
from src.ui.views.user_management_view import render_user_management_view
from src.ui.views.student_portal_view import render_student_portal_view


# ---------------- SESSION AND ACCESS CONTROL ----------------

if "auth_session" not in st.session_state or st.session_state.auth_session is None:
    render_login_view()
    st.stop()

# Check session expiration
if is_session_expired(st.session_state.auth_session, timeout_minutes=DEFAULT_SESSION_TIMEOUT_MINUTES):
    st.session_state.auth_session = None
    st.warning("Your session has timed out due to inactivity. Please sign in again.")
    st.rerun()

# Update activity timestamp
refresh_session_activity(st.session_state.auth_session)
current_user = st.session_state.auth_session["user"]
user_role = current_user.get("role", "student")


# ---------------- SIDEBAR NAVIGATION ----------------

with st.sidebar:
    st.markdown("### 🎓 Academic Portal")
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.08); padding: 14px; border-radius: 8px; margin-bottom: 20px;">
        <div style="font-size: 15px; font-weight: 700; color: #ffffff;">{current_user.get('full_name')}</div>
        <div style="font-size: 13px; color: #94a3b8;">@{current_user.get('username')}</div>
        <div style="margin-top: 8px;">
            <span style="background: #2563eb; color: #ffffff; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase;">
                {user_role}
            </span>
            {f'<span style="background: rgba(255,255,255,0.15); color: #e2e8f0; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 6px;">{current_user.get("linked_student_id")}</span>' if current_user.get("linked_student_id") else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Role-Based Navigation Menu Options
    if user_role == "admin":
        nav_options = [
            "📊 Executive Dashboard",
            "👥 Student Management",
            "🎯 Student Profile & ML Prediction",
            "⚡ Instant Simulator",
            "📁 Batch Student Screening",
            "📈 Model Benchmarks & Metrics",
            "🔬 Exploratory Data Analysis (EDA)",
            "⚙️ User Administration"
        ]
    elif user_role == "faculty":
        nav_options = [
            "📊 Executive Dashboard",
            "👥 Student Management",
            "🎯 Student Profile & ML Prediction",
            "⚡ Instant Simulator",
            "📁 Batch Student Screening",
            "📈 Model Benchmarks & Metrics",
            "🔬 Exploratory Data Analysis (EDA)"
        ]
    else:  # student role
        nav_options = [
            "🎓 My Academic Profile & Trajectory"
        ]

    # Preserve current navigation page state
    if "current_page" not in st.session_state or st.session_state.current_page not in [opt.split(" ", 1)[1] for opt in nav_options]:
        st.session_state.current_page = nav_options[0].split(" ", 1)[1]

    # Map option back to index
    default_idx = 0
    for idx, opt in enumerate(nav_options):
        if opt.split(" ", 1)[1] == st.session_state.current_page:
            default_idx = idx
            break

    selected_nav = st.radio(
        "Navigation Menu",
        options=nav_options,
        index=default_idx
    )
    clean_page_name = selected_nav.split(" ", 1)[1]
    st.session_state.current_page = clean_page_name

    st.markdown("---")
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.auth_session = None
        st.session_state.current_page = None
        st.session_state.active_student_id = None
        st.rerun()

    st.markdown("""
    <div style="font-size: 11.5px; color: #94a3b8; text-align: center; margin-top: 30px; line-height: 1.4;">
        <b>Student Academic Success Predictor</b><br>
        Candidate: Asmita C. Kumbar<br>
        SYBSc CS | Roll: SI1161<br>
        Supervised ML & EDM System
    </div>
    """, unsafe_allow_html=True)


# ---------------- MAIN CONTENT AREA ----------------

render_header(user=current_user)

page = st.session_state.current_page

if page == "Executive Dashboard":
    render_dashboard_view()
elif page == "Student Management":
    render_student_management_view(user=current_user)
elif page == "Student Profile & ML Prediction":
    render_student_profile_view(user=current_user)
elif page == "Instant Simulator":
    render_instant_prediction_view(user=current_user)
elif page == "Batch Student Screening":
    render_batch_screening_view(user=current_user)
elif page == "Model Benchmarks & Metrics":
    render_benchmarks_view()
elif page == "Exploratory Data Analysis (EDA)":
    render_eda_view()
elif page == "User Administration":
    render_user_management_view(current_user=current_user)
elif page == "My Academic Profile & Trajectory":
    render_student_portal_view(user=current_user)
else:
    render_dashboard_view()

# Global Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 12.5px; padding: 10px 0;">
    Academic Project: <b>Predicting Student Academic Success & Exam Outcomes Using Supervised Machine Learning</b><br>
    Submitted by <b>Asmita Chandram Kumbar</b> (SYBSc CS, Roll No: SI1161) | Department of Computer Science
</div>
""", unsafe_allow_html=True)
