"""
Premium CSS styling and theme configuration for the Student Academic Success Prediction System.
Color Palette:
- Deep Navy: #0f172a / #1e293b
- Academic Blue: #1e3a8a / #2563eb / #3b82f6
- Soft Backgrounds: #f8fafc / #f1f5f9
- Accents & Status:
  - Success / Low Risk: #059669 / #10b981 / #ecfdf5
  - Warning / Moderate Risk: #d97706 / #f59e0b / #fffbeb
  - Danger / High Risk: #dc2626 / #ef4444 / #fef2f2
"""

MAIN_CSS = """
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Top App Header */
    .edu-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #2563eb 100%);
        padding: 24px 30px;
        border-radius: 12px;
        color: #ffffff;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.15);
    }
    .edu-header h1 {
        color: #ffffff !important;
        font-size: 26px !important;
        font-weight: 700 !important;
        margin: 0 0 6px 0 !important;
        letter-spacing: -0.02em;
    }
    .edu-header p {
        color: #e2e8f0 !important;
        font-size: 14px !important;
        margin: 0 0 14px 0 !important;
        opacity: 0.95;
    }
    .edu-badge-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
    }
    .edu-badge {
        background: rgba(255, 255, 255, 0.16);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.25);
        color: #ffffff;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .edu-badge-role {
        background: #ffffff;
        color: #1e3a8a;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Metric Cards */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 20px 22px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        margin-bottom: 12px;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
    }
    .kpi-label {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
    }
    .kpi-subtitle {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* Risk Cards */
    .risk-banner-low {
        background-color: #ecfdf5;
        border: 1px solid #a7f3d0;
        border-left: 6px solid #059669;
        border-radius: 8px;
        padding: 18px 20px;
        color: #065f46;
        margin-bottom: 16px;
    }
    .risk-banner-mod {
        background-color: #fffbeb;
        border: 1px solid #fde68a;
        border-left: 6px solid #d97706;
        border-radius: 8px;
        padding: 18px 20px;
        color: #92400e;
        margin-bottom: 16px;
    }
    .risk-banner-high {
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 6px solid #dc2626;
        border-radius: 8px;
        padding: 18px 20px;
        color: #991b1b;
        margin-bottom: 16px;
    }

    /* Intervention Card */
    .intervention-panel {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    .intervention-panel h4 {
        color: #0f172a;
        margin-top: 0;
        margin-bottom: 12px;
        font-weight: 600;
    }
    .intervention-item {
        padding: 10px 14px;
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        border-radius: 4px;
        margin-bottom: 8px;
        font-size: 13.5px;
        color: #334155;
        line-height: 1.45;
    }

    /* Profile Details Card */
    .profile-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }
    .profile-header {
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 12px;
        margin-bottom: 16px;
    }
    .profile-header h3 {
        margin: 0;
        color: #0f172a;
        font-weight: 700;
    }

    /* Auth Form Card */
    .auth-container {
        max-width: 480px;
        margin: 40px auto;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 30px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    }

    /* Sidebar Clean Styling */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        color: #f8fafc;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: #f1f5f9 !important;
    }

    /* Clean Buttons */
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.15s ease;
    }
</style>
"""


def apply_custom_css():
    """Returns CSS block to be embedded via st.markdown."""
    return MAIN_CSS
