# Flask Migration & Enhancement Plan: AI-Based Student Performance Prediction System

## 1. Project Background & Context
- **Candidate:** Asmita Chandram Kumbar (SYBSc CS, Roll No: SI1161)
- **Objective:** Redesign the Student Academic Success Prediction System from Streamlit into a robust, secure, production-grade Flask full-stack web application with Jinja2 templates, Bootstrap 5, SQLite persistence, and explainable ML inference.
- **Top Priority:** Guaranteed, bulletproof authentication & session management with role-based access control, zero data loss, and safe database migrations.

---

## 2. Architecture & File Structure

```
student_success_prediction/
├── backups/                          # SQLite database backups
│   ├── student_success.db
│   └── student_success_backup.db
├── database/
│   └── student_success.db            # Canonical SQLite database
├── docs/
│   ├── MIGRATION_PLAN.md             # This migration document
│   └── ASSUMPTIONS.md                # System assumptions and role specs
├── flask_app/                        # New Flask application package
│   ├── __init__.py                   # Application factory (create_app)
│   ├── config.py                     # Dev / Prod / Test configurations
│   ├── models.py                     # SQLAlchemy models & helper mappers
│   ├── forms.py                      # WTForms with CSRF & server validation
│   ├── blueprints/
│   │   ├── auth/                     # Login, register, logout, profile
│   │   ├── main/                     # Dashboard, KPIs, needs attention
│   │   ├── students/                 # Student CRUD, search, filter, export
│   │   ├── predictions/              # Predict, explainable AI, batch, simulator
│   │   ├── transparency/             # Model metrics, confusion matrix, about
│   │   ├── interventions/            # Intervention tracker & follow-up alerts
│   │   ├── audit/                    # Audit logging viewer (admin only)
│   │   └── api/                      # Health check & JSON endpoints
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css             # Design tokens, dark/light theme, custom styling
│   │   └── js/
│   │       └── main.js               # Theme toggle, submit debounce, Chart.js helpers
│   └── templates/
│       ├── base.html                 # Common layout with sidebar, navbar, flash alerts
│       ├── errors/ (403, 404, 500)
│       ├── auth/ (login, register, profile)
│       ├── dashboard/ (index)
│       ├── students/ (list, detail, form)
│       ├── predictions/ (predict, batch, simulator)
│       ├── transparency/ (index, about)
│       ├── interventions/ (index)
│       └── audit/ (index)
├── src/                              # Preserved business logic & ML services
│   ├── db/
│   │   ├── connection.py             # Existing connection manager (WAL mode, FKs)
│   │   ├── schema.py                 # Existing schema definitions
│   │   ├── migrate.py                # CSV-to-SQLite data loader
│   │   └── migrate_enhancements.py   # Safe migrations for interventions & audit logs
│   └── services/
│       ├── auth_service.py           # Core auth & permission checks
│       ├── student_service.py        # Core student CRUD & pagination
│       ├── prediction_service.py     # ML inference, explainability & risk mapping
│       └── academic_history_service.py# 4-year transcript service
├── tests/
│   ├── test_flask_auth.py            # Comprehensive Flask-Login & session tests
│   ├── test_flask_rbac.py            # Role enforcement and IDOR prevention
│   ├── test_flask_features.py        # Core student, prediction, report tests
│   ├── test_enhancements.py          # Explainability, audit log, interventions tests
│   └── conftest.py                   # Pytest fixtures with temporary DB & Flask client
├── run_flask.py                      # Production / dev CLI entrypoint
└── wsgi.py                           # WSGI entrypoint
```

---

## 3. Database Strategy & Data Preservation
- **Location:** Canonical path `database/student_success.db` retained. All services and Flask configs reference this path.
- **Backups:** Timestamped and initial backups stored in `backups/`.
- **Schema Migration:** An idempotent migration script (`src/db/migrate_enhancements.py`) adds:
  - `interventions` table (id, student_id, title, description, status, follow_up_date, created_by, created_at, updated_at).
  - `audit_logs` table (id, user_id, username, action, target, details, ip_address, created_at).
  - `top_factors_json` column to `prediction_history` (via `ALTER TABLE` if not exists).
  - `last_login` column to `users` (via `ALTER TABLE` if not exists).
- **Rule:** Never execute `DROP TABLE` or recreate database. SQLite `PRAGMA foreign_keys = ON;` and `PRAGMA journal_mode = WAL;` are strictly enforced.

---

## 4. Security & Authentication Architecture
- **Flask-Login:** User session tracking with strong session protection (`session_protection = "strong"`).
- **CSRF Protection:** Enabled globally using `Flask-WTF` `CSRFProtect`. Every form includes `csrf_token`.
- **Password Security:** Werkzeug `generate_password_hash` (`pbkdf2:sha256` or `scrypt`) with salt. No plaintext passwords stored.
- **Session Security:**
  - `SESSION_COOKIE_HTTPONLY = True`
  - `SESSION_COOKIE_SAMESITE = 'Lax'`
  - `SESSION_COOKIE_SECURE = False` in Dev, configurable to `True` via `SECURE_COOKIES=1` in production.
  - Permanent session lifetime: 60 minutes.
- **Cache-Control:** `@no_cache` decorator applied to all authenticated routes to prevent back-button access after logout (`no-store, no-cache, must-revalidate, max-age=0`).
- **Logout:** Explicit POST route with CSRF validation that invokes `logout_user()`, clears `session`, and redirects cleanly.
- **Brute-Force Protection:** IP/username attempt tracker in memory/cache with exponential backoff / lockout after 5 failed attempts within 15 minutes.
- **Open Redirect Guard:** `is_safe_url()` validation for any `next` parameter to prevent external redirection.

---

## 5. Explainable AI & Machine Learning Pipeline
- Real model weights from `models/logistic_regression_coefficients.csv` and `models/scaler.joblib`.
- Top 3 contributing factors calculated by ranking standardized feature contribution $w_i \cdot \frac{x_i - \mu_i}{\sigma_i}$.
- Color + text risk level badges:
  - High Risk: Red (`pass_prob < 0.50`)
  - Moderate Risk: Yellow (`0.50 <= pass_prob < 0.75`)
  - Low Risk: Green (`pass_prob >= 0.75`)
- Ethical disclaimer: *"Predictions support teacher judgment and are not final decisions."*
- Features strictly exclude target columns (`final_exam_score`, `passed`) to eliminate data leakage.

---

## 6. Risks & Mitigations
| Risk | Severity | Mitigation |
| :--- | :---: | :--- |
| Accidental SQLite lock during concurrent writes | Low | Enable WAL mode (`PRAGMA journal_mode = WAL;`) and 30-second busy timeout. |
| Inadvertent admin creation via public registration | Critical | Public registration strictly assigns `role='student'`. Admin creation only through secure CLI `create_admin.py`. |
| IDOR / unauthorized student access | High | Access control helper `can_view_student()` checks user role and linked student ID in both backend services and view routes. |
| Model deserialization mismatch across Python/sklearn versions | Medium | Wrap model loading in `try-except`, provide fallback informative error page and transparent status message. |
| Session fixation attack | High | Session regenerated on login and cleared completely on logout. |
