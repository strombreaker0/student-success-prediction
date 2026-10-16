# 🎓 Predicting Student Academic Success and Exam Outcomes Using Supervised Machine Learning

### 📌 Project Synopsis & Academic Submission
* **Student Name:** Asmita Chandram Kumbar  
* **Class:** SYBSc CS (Second Year Bachelor of Science - Computer Science)  
* **Roll No:** SI1161  
* **Academic Year:** 2nd Year  
* **Department:** Department of Computer Science  
* **Domain:** Educational Data Mining & Supervised Machine Learning  

---

## 🌟 Executive Summary
Academic performance is a vital indicator of institutional efficacy and student well-being. Traditional tracking mechanisms are primarily **reactive**, identifying underperforming students only after semester grades or exam failures are published. 

This upgraded system implements an enterprise-grade, **proactive machine learning classification and educational analytics platform**. It couples supervised learning pipelines (**Logistic Regression**, **Decision Tree**, and **Random Forest**) with a persistent **SQLite database**, **Role-Based Access Control (RBAC)**, a **Four-Year Student Academic Progress Portal**, an **interactive Student Management module**, **batch risk screening**, and **automated intervention generation**.

---

## 🎯 System Capabilities & Architecture

```
student_success_prediction/
│
├── database/
│   ├── student_success.db       # Persistent SQLite store (WAL mode, FK constraints)
│   └── student_success_backup.db # Safety backup of SQLite database
│
├── data/
│   ├── generate_dataset.py      # Synthetic student cohort generator
│   └── student_data.csv         # 1,200 records with academic & behavioral features (backup)
│
├── models/
│   ├── imputer.joblib           # Trained median imputer
│   ├── scaler.joblib            # Trained standard scaler
│   ├── logistic_regression_model.joblib
│   ├── decision_tree_model.joblib
│   ├── random_forest_model.joblib
│   ├── evaluation_metrics.json  # Stored performance scores
│   └── logistic_regression_coefficients.csv
│
├── reports/
│   └── figures/                 # High-resolution publication figures
│       ├── 1_attendance_vs_outcome.png
│       ├── 2_study_hours_vs_score.png
│       ├── 3_correlation_matrix.png
│       ├── 4_feature_coefficients.png
│       ├── 5_confusion_matrices.png
│       └── 6_roc_curves.png
│
├── src/
│   ├── db/                      # Database & Migration Layer
│   │   ├── connection.py        # SQLite connection factory (WAL mode, row_factory)
│   │   ├── schema.py            # Normalized tables: students, users, predictions, 4-year history
│   │   ├── migrate.py           # Idempotent CSV-to-SQLite migration pipeline
│   │   └── migrate_academic_history.py # Safe 4-year academic history schema migration
│   │
│   ├── services/                # Business Logic & Security Services
│   │   ├── auth_service.py      # PBKDF2 password hashing, RBAC, session timeout
│   │   ├── student_service.py   # Student CRUD, validation ranges, search/filter, CSV export
│   │   ├── academic_history_service.py # 4-Year history, SGPA/CGPA analytics, PDF/CSV transcripts
│   │   └── prediction_service.py# Model inference, risk tiering, intervention guidance, history
│   │
│   ├── ui/                      # Premium UI & Presentation Layer
│   │   ├── styles.py            # Custom CSS theme (Navy/Blue/Slate)
│   │   ├── components.py        # Reusable metric cards, badges, banners
│   │   └── views/               # Modularized UI views
│   │       ├── login_view.py
│   │       ├── dashboard_view.py
│   │       ├── student_management_view.py
│   │       ├── student_profile_view.py  # 4-Year history & grade card management
│   │       ├── student_portal_view.py   # Student self-service 4-year progress portal
│   │       ├── instant_prediction_view.py
│   │       ├── batch_screening_view.py
│   │       ├── benchmarks_view.py
│   │       ├── eda_view.py
│   │       └── user_management_view.py
│   │
│   ├── preprocess.py            # Core feature preprocessing pipeline
│   ├── train_models.py          # Supervised model training & evaluation
│   └── eda_visualizations.py    # Figure generation scripts
│
├── tests/                       # Automated Test Suite (27 unit & integration tests)
│   ├── test_auth.py
│   ├── test_student_service.py
│   ├── test_prediction_service.py
│   ├── test_four_year_academic_history.py
│   ├── test_migrate.py
│   └── test_e2e_integration.py
│
├── app.py                       # Upgraded Streamlit Web Application entrypoint
├── init_db.py                   # Standalone database initialization & migration tool
├── create_admin.py              # Secure administrator setup script
├── predict_cli.py               # Interactive Command-Line Prediction Tool
├── Student_Success_Prediction.ipynb # Jupyter Notebook for Colab / viva evaluation
├── run_app.bat                  # One-click Windows launcher for Web App
├── run_cli.bat                  # One-click Windows launcher for CLI Tool
├── requirements.txt             # Project library dependencies (includes reportlab & werkzeug)
└── README.md                    # Project documentation
```

---

## 🎓 Four-Year Student Academic Progress Portal

The platform features an integrated four-year academic lifecycle management subsystem:

1. **Normalized Database Architecture**:
   * `academic_year_records`: Stores Year 1 (FE), Year 2 (SE), Year 3 (TE), and Year 4 (BE) summary standings, academic session, year CGPA, and status.
   * `semester_results`: Stores Semester 1 through Semester 8 results, SGPA, credits attempted/earned, attendance %, coursework submission %, and mentor remarks.
   * `subject_results`: Stores course-level subject code, name, credits, internal marks ($/20$), external marks ($/80$), total marks ($/100$), letter grade ($O, A+, A, B+, B, C, P, F$), and grade points.
   * `student_activities`: Stores co-curricular projects, research internships, industry certificates, and student competition awards.
2. **Student Self-Service Dashboard**:
   * **Overall Progress Overview**: Live Cumulative CGPA (10-point scale), total credits earned, semesters completed, and overall attendance.
   * **Four-Year Timeline**: Expandable grade cards for Year 1 to Year 4 with unrecorded semesters labeled cleanly as *Not Recorded* or *In Progress*.
   * **Interactive Analytics Trends**: Matplotlib progression charts for SGPA trajectories and semester-wise attendance vs. assignment completion.
   * **Strengths & Growth Areas**: Highlights high-grade subjects ($O, A+$) and flags attendance or coursework deficits.
   * **Official Transcripts**: One-click download of a publication-ready **PDF Academic Transcript** (generated with `ReportLab`) or **CSV Record Export**.
   * **Proactive ML Evaluation**: Real-time pass/fail probability gauge, risk level, and tailored remedial intervention guidance.
3. **Faculty & Administrator Management Workflow**:
   * Authorized educators can access any student's profile via *Student Directory* -> *Student Profile & Four-Year Progress Management* to enter/update semester SGPA, record individual subject marks, or add co-curricular achievements.

---

## 🔐 Authentication & Role-Based Access Control (RBAC)

The system enforces strict access policies at both the UI and database service layer:

| Role | Permissions & Scope |
| :--- | :--- |
| **Admin** | Full system control: Manage student records (Add, Edit, Delete), provision user accounts & roles, enter/update 4-year academic history & subject grades, run predictions, batch screening, view dashboard, benchmarks, and EDA. |
| **Faculty** | Educational management: View all student records, Add/Edit student records, record semester & subject results, log co-curricular achievements, run individual ML predictions, batch screening, view dashboard, benchmarks, and EDA. |
| **Student** | Student self-service: View **strictly their own** academic profile across all 4 years, semester grade cards, interactive charts, achievements, latest ML success prediction, personalized interventions, and download official transcripts. Cross-student access is strictly blocked. |

* **Password Security**: Passwords are never stored in plaintext; hashed with salted PBKDF2-SHA256 via `Werkzeug`.
* **Session Management**: Automated session expiration check with inactivity timeouts.
* **Student Account Linking**: Every student user is cryptographically authenticated and linked to exactly one `student_id` via `linked_student_id`.

---

## 📊 Experimental Results & Model Benchmarks

Tested on an independent, unseen test dataset of 240 student records (80/20 stratified split):

| Algorithm | Accuracy | Precision | Recall (Sensitivity) | F1-Score | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Primary)** | **80.00%** | **81.46%** | **90.62%** | **85.80%** | **0.8495** |
| **Random Forest Classifier** | 77.92% | 78.01% | 93.12% | 84.90% | 0.8274 |
| **Decision Tree Classifier** | 74.17% | 75.52% | 90.62% | 82.39% | 0.7580 |

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites
- Python 3.8+ (tested on Python 3.13 on Windows 10/11)
- PowerShell or Windows Command Prompt

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Initialize Database & Four-Year History Schema
Initialize the SQLite tables and migrate all 1,200 records from `data/student_data.csv`:
```powershell
python init_db.py
```
To run the safe Four-Year Academic History migration:
```powershell
python -m src.db.migrate_academic_history
```

### 4. Create Initial Administrator Account
Bootstrap your administrator credentials safely (interactive password entry with no hardcoded secrets):
```powershell
python create_admin.py
```

### 5. Launch the Web Application
Double-click `run_app.bat` or run:
```powershell
python -m streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 6. Run the Automated Test Suite (27 Tests)
Run the complete automated test suite covering authentication, RBAC, student CRUD, ML prediction integration, 4-year academic history, transcript exports, and migrations:
```powershell
python -m pytest -v
```

---
**Submitted for SYBSc Computer Science Evaluation by Asmita Chandram Kumbar (Roll No: SI1161)**
