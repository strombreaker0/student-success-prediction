# 🎓 Predicting Student Academic Success and Exam Outcomes Using Supervised Machine Learning

### 📌 Project Synopsis & Academic Credentials
* **Student Name:** Asmita Chandram Kumbar  
* **Class:** Second Year Bachelor of Science - Computer Science (SYBSc CS)  
* **Roll No:** SI1161  
* **Academic Year:** 2nd Year  
* **Department:** Department of Computer Science  
* **Domain:** Educational Data Mining (EDM) & Supervised Machine Learning  

---

## 🌟 Executive Summary
Academic underperformance incurs severe emotional and financial costs to students and educational institutions. Traditional evaluation approaches rely on post-facto metrics (such as semester grade cards), discovering academic distress after failure has already occurred.

This system provides a **production-grade Flask educational analytics and machine learning decision-support web platform**. Built with a modular Flask application factory architecture, Blueprints, Jinja2 templates, Bootstrap 5, SQLite persistence (with WAL mode and foreign key integrity), and Scikit-Learn supervised classification pipelines (**Logistic Regression**, **Decision Tree**, and **Random Forest**), the application enables educators to proactively identify at-risk learners and prescribe personalized remedial interventions.

---

## 🔒 Top Priority: Bulletproof Authentication & Security
* **Authentication Engine:** Powered by `Flask-Login` and `Flask-WTF` with strong session protection (`session_protection = "strong"`).
* **Password Hashing:** Werkzeug secure cryptographic hashing (`scrypt` / `pbkdf2:sha256`) with unique per-user salts.
* **CSRF Protection:** Globally enforced via `CSRFProtect`; all forms and state-changing requests require a cryptographically validated token.
* **Brute-Force Protection:** In-memory rate limiting and exponential lockout after 5 consecutive failed login attempts.
* **Credential Enumeration Defense:** Uniform generic error messages (*"Invalid username/email or password."*) ensure account existence is never leaked.
* **Session Fixation & Back-Button Protection:** Session IDs are regenerated upon login and cleared entirely upon logout. All authenticated views carry aggressive HTTP headers (`Cache-Control: no-store, no-cache, must-revalidate, max-age=0`) to prevent back-button access post-logout.
* **Role-Based Access Control (RBAC):**
  - **Administrator:** Full clearance across students, user administration, system-wide audit logs, and batch operations.
  - **Faculty / Teacher:** Cohort student management, real-time prediction running, intervention tracking, and model transparency. Blocked from system user administration, record deletion, and security audit logs.
  - **Student:** Strict self-service isolation. Can ONLY view their linked academic record and personalized predictions. Direct URL manipulation across student IDs is blocked (IDOR prevention).
  - **Public Self-Registration:** Strictly assigns `role='student'`. Administrative provisioning is restricted to secure CLI commands.

---

## 🏗️ System Architecture & Directory Structure

```
student_success_prediction/
├── backups/                          # Timestamped SQLite database safety backups
│   ├── student_success.db
│   └── student_success_backup.db
├── database/
│   └── student_success.db            # Canonical SQLite database (WAL mode, FKs)
├── data/
│   ├── generate_dataset.py           # Cohort data generation script
│   └── student_data.csv              # 1,200 student baseline cohort dataset
├── docs/
│   ├── MIGRATION_PLAN.md             # Written Flask architecture and migration plan
│   └── ASSUMPTIONS.md                # System assumptions, role matrix, and specs
├── flask_app/                        # Production Flask Web Application Package
│   ├── __init__.py                   # Application factory (create_app) & CLI commands
│   ├── config.py                     # Dev / Prod / Test configuration classes
│   ├── models.py                     # Flask-Login User model & RBAC helpers
│   ├── forms.py                      # WTForms with CSRF & server validation
│   ├── security.py                   # Role guards, no-cache headers, safe redirect validator
│   ├── blueprints/
│   │   ├── auth/                     # Login, register, logout, profile
│   │   ├── main/                     # Executive dashboard & needs-attention panel
│   │   ├── students/                 # Student CRUD, search, pagination, bulk upload, PDF
│   │   ├── predictions/              # Real-time ML inference, batch screening, simulator
│   │   ├── transparency/             # Model evaluation benchmarks, confusion matrix, about
│   │   ├── interventions/            # Remedial action plans & follow-up milestones
│   │   ├── audit/                    # Append-only security audit log viewer (admin only)
│   │   └── api/                      # Health check (/health) and simulation endpoints
│   ├── static/
│   │   ├── css/style.css             # Educational analytics design tokens (Dark/Light)
│   │   └── js/main.js                # Theme toggle, form debouncing, quick search
│   └── templates/
│       ├── base.html                 # Common responsive layout with sidebar and topbar
│       ├── errors/ (403, 404, 500)   # Custom branded error pages
│       ├── auth/                     # login.html, register.html, profile.html
│       ├── dashboard/                # index.html, student_unlinked.html
│       ├── students/                 # list.html, detail.html, form.html, bulk_upload.html
│       ├── predictions/              # predict.html, batch.html, simulator.html
│       ├── transparency/             # index.html, about.html
│       ├── interventions/            # index.html
│       └── audit/                    # index.html
├── models/                           # Trained ML artifacts & serialized pipelines
│   ├── imputer.joblib                # Median imputation artifact
│   ├── scaler.joblib                 # Z-Score standard scaling artifact
│   ├── logistic_regression_model.joblib
│   ├── decision_tree_model.joblib
│   ├── random_forest_model.joblib
│   ├── evaluation_metrics.json       # Precomputed test evaluation scores
│   └── logistic_regression_coefficients.csv
├── src/                              # Core Domain Services & DB Connectors
│   ├── db/
│   │   ├── connection.py             # SQLite connection manager (WAL, FKs, timeout)
│   │   ├── schema.py                 # SQLite schema definitions
│   │   ├── migrate.py                # CSV-to-SQLite initial migration
│   │   └── migrate_enhancements.py   # Safe, idempotent enhancements migration
│   └── services/
│       ├── auth_service.py           # Core authentication, password hashing, rate limiting
│       ├── student_service.py        # Student CRUD, validation, search, export
│       ├── prediction_service.py     # Supervised ML inference, explainability, risk tiers
│       ├── intervention_service.py   # Remedial intervention workflows and overdue tracking
│       ├── audit_service.py          # Append-only audit logging and credential masking
│       ├── academic_history_service.py# 4-year transcript service
│       └── pdf_service.py            # ReportLab student assessment dossier generator
├── tests/                            # Automated Pytest Suite (60 tests)
│   ├── conftest.py                   # Isolated temporary DB fixtures
│   ├── test_flask_auth_and_security.py
│   ├── test_flask_rbac_and_isolation.py
│   ├── test_flask_core_features.py
│   ├── test_enhancements_suite.py
│   ├── test_auth.py
│   ├── test_student_service.py
│   ├── test_prediction_service.py
│   ├── test_four_year_academic_history.py
│   ├── test_migrate.py
│   └── test_e2e_integration.py
├── run_flask.py                      # Local Windows development server launcher
├── wsgi.py                           # Production WSGI application entrypoint
├── .env.example                      # Environment variable template
├── requirements.txt                  # Pinned dependencies
└── README.md                         # Documentation
```

---

## 🧠 Machine Learning & Explainable AI Specifications

### 1. Empirical Model Performance (Stratified 80/20 Test Split, N=240)
| Metric | Logistic Regression (Primary) | Decision Tree | Random Forest |
| :--- | :---: | :---: | :---: |
| **Accuracy** | **80.00%** | 74.17% | 77.92% |
| **Precision** | **81.46%** | 75.52% | 78.01% |
| **Recall (Sensitivity)** | **90.62%** | 90.62% | **93.13%** |
| **F1-Score** | **85.80%** | 82.39% | 84.90% |
| **ROC-AUC** | **0.8495** | 0.7580 | 0.8274 |

### 2. Explainable Predictions
On every prediction, the system mathematically calculates the top 3 contributing factors in human-readable language using the standardized log-odds contribution ($w_j \cdot z_j$):
- Features are normalized ($z_j = \frac{x_j - \mu_j}{\sigma_j}$) using the training distribution.
- The highest absolute contributions to passing or failing odds are extracted and presented with directional indicators (+ / -).
- Color-plus-text risk stratification badges:
  - **Low Risk:** Pass Likelihood $\ge 75\%$
  - **Moderate Risk:** $50\% \le$ Pass Likelihood $< 75\%$
  - **High Risk:** Pass Likelihood $< 50\%$
- Mandatory Advisory Notice: *"Predictions support teacher judgment and are not final decisions."*
- Features strictly exclude target labels (`final_exam_score`, `passed`) to eliminate data leakage.

### 3. What-If Academic Simulator
An interactive tool featuring range sliders for attendance rate, study hours, previous scores, assignment completion, tutoring sessions, and sleep hours. Calls the real model pipeline dynamically to demonstrate how behavior modifications alter predicted exam outcomes. Labeled prominently as a simulation and **never** stored in database prediction history.

### 4. Automated PDF Dossier Generation
Integrates `ReportLab 5.0` to generate individual student assessment dossiers containing student profile metrics, predictive risk assessments, top explainable factors, and remedial intervention plans.

---

## 💻 Windows PowerShell Setup & Execution Guide

Follow these exact commands in **Windows PowerShell (VS Code terminal)**:

### 1. Create and Activate Virtual Environment
```powershell
# Create Python virtual environment
python -m venv venv

# Activate virtual environment in PowerShell
.\venv\Scripts\Activate.ps1
```

### 2. Install Project Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Safely Run Database Migrations
```powershell
# Executes idempotent schema migration (zero data loss, creates interventions and audit_logs)
python -m src.db.migrate_enhancements
```

### 4. Create an Administrator Account (Secure CLI Method)
```powershell
# Interactive CLI admin provisioning (never hardcoded in source)
python -m flask --app flask_app create-admin
```

### 5. Start the Web Application
```powershell
python run_flask.py
```
- **Local Application URL:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Health Check Endpoint:** [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health)

### 6. Run the Full Automated Test Suite
```powershell
python -m pytest -v
```
All **60 tests** run on isolated temporary databases, verifying authentication, security, RBAC, IDOR protection, ML explainability, and reporting.

---

## 📜 Academic Project Information
* **Candidate:** Asmita Chandram Kumbar  
* **Roll Number:** SI1161  
* **Class:** Second Year B.Sc. Computer Science (SYBSc CS)  
* **Project Title:** Predicting Student Academic Success and Exam Outcomes Using Supervised Machine Learning  
* **Submission Date:** Academic Term 2026  
