"""
Reusable UI components for the Student Academic Success Prediction System.
"""

import streamlit as st


def render_header(user: dict | None = None):
    """Renders the top banner with academic context, candidate credentials, and user role."""
    role_badge = ""
    user_info = ""

    if user:
        role_label = user.get('role', 'User').capitalize()
        name = user.get('full_name', user.get('username', ''))
        role_badge = f'<span class="edu-badge edu-badge-role">{role_label}</span>'
        user_info = f'<span class="edu-badge">Signed in: <b>{name}</b></span>'

    st.markdown(f"""
    <div class="edu-header">
        <h1>Predicting Student Academic Success & Exam Outcomes</h1>
        <p>Educational Data Mining & Supervised Machine Learning Decision-Support System</p>
        <div class="edu-badge-bar">
            {role_badge}
            {user_info}
            <span class="edu-badge">Candidate: <b>Asmita Chandram Kumbar</b></span>
            <span class="edu-badge">Class: <b>SYBSc CS (2nd Year)</b></span>
            <span class="edu-badge">Roll No: <b>SI1161</b></span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_card(label: str, value: str | int | float, subtitle: str = "", border_color: str = "#2563eb"):
    """Renders an attractive KPI summary card with color accent."""
    st.markdown(f"""
    <div class="kpi-card" style="border-left: 5px solid {border_color};">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def render_risk_result(pred_result: dict):
    """Renders the prediction result box and risk categorization."""
    outcome = pred_result.get("outcome_label", "Unknown")
    pass_prob = pred_result.get("pass_probability_pct", 0.0)
    fail_prob = pred_result.get("fail_probability_pct", 0.0)
    risk = pred_result.get("risk_category", "Unknown")
    model_name = pred_result.get("model_name", "Model")

    if risk == "Low Risk":
        css_class = "risk-banner-low"
        title_icon = "Safe / Passing Zone"
        status_sub = "Student is on an established trajectory for examination success."
    elif risk == "Moderate Risk":
        css_class = "risk-banner-mod"
        title_icon = "Moderate Risk Zone"
        status_sub = "Student trajectory is viable but vulnerable to academic disruptions."
    else:
        css_class = "risk-banner-high"
        title_icon = "High Risk / Academic Support Required"
        status_sub = "Immediate institutional intervention required to prevent exam failure."

    st.markdown(f"""
    <div class="{css_class}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <h3 style="margin: 0; font-weight: 700;">{title_icon} ({outcome.upper()})</h3>
            <span style="font-size: 13px; font-weight: 600; padding: 3px 8px; border-radius: 4px; background: rgba(0,0,0,0.06);">
                {model_name}
            </span>
        </div>
        <div style="font-size: 15px; margin-bottom: 4px;">
            <b>Pass Probability:</b> {pass_prob:.1f}% &nbsp;|&nbsp; <b>Failure Risk:</b> {fail_prob:.1f}% &nbsp;|&nbsp; <b>Risk Tier:</b> {risk}
        </div>
        <div style="font-size: 13px; opacity: 0.9;">
            {status_sub}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Visual Likelihood Gauge
    st.progress(float(pass_prob) / 100.0, text=f"Predicted Probability of Passing: {pass_prob:.1f}%")


def render_interventions_box(interventions: list[str]):
    """Renders the structured intervention plan."""
    st.markdown("""
    <div class="intervention-panel">
        <h4>Actionable Pedagogical Interventions</h4>
    </div>
    """, unsafe_allow_html=True)

    if not interventions:
        st.info("No specific intervention flags detected. Maintain current study routine.")
        return

    for item in interventions:
        st.markdown(f"""
        <div class="intervention-item">
            {item}
        </div>
        """, unsafe_allow_html=True)
