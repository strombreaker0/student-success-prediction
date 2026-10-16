# System Assumptions and Technical Specifications

This document records architectural decisions, domain assumptions, and role-based policies for the **AI-Based Student Academic Success Prediction System**.

---

## 1. User Roles & Authorization Hierarchy

| Role in System | Equivalent in Report / Requirements | Permissions |
| :--- | :--- | :--- |
| **admin** | Administrator | Full read/write access to all students, user management, audit logs, model metrics, system settings, database backups, and batch screening. |
| **faculty** | Teacher / Faculty Advisor | Access to all students in academic cohort, student profile editing, academic history recording, real-time prediction running, intervention tracking, and batch screening. Cannot manage system users or view system-wide audit logs. |
| **student** | Student Learner | Strict self-service access: can ONLY view their own student profile, academic history, and personalized predictions. Denied access to batch screening, user management, and other students' profiles (IDOR prevented). |

---

## 2. Authentication & Account Creation Policies
1. **Public Self-Registration:**
   - Any visitor can register for an account via `/auth/register`.
   - The system automatically forces the role to **`student`**.
   - Public registration CANNOT create `admin` or `faculty` accounts under any circumstance.
   - An optional `linked_student_id` can be specified during registration if the student exists in the database.
2. **Administrative Provisioning:**
   - The first administrator is bootstrapped securely via `create_admin.py` or interactive CLI script.
   - Additional `faculty` and `admin` accounts can only be created by an authenticated `admin` via User Management.
3. **Session Lifetime:**
   - Default session timeout is 60 minutes of inactivity.
   - Re-authentication is required upon timeout.

---

## 3. Database & Entity Assumptions
1. **Database Path:**
   - All components, scripts, and tests connect to `database/student_success.db` by default, overridable by the `STUDENT_DB_PATH` environment variable.
2. **Student Identifier Schema:**
   - Student IDs follow the standard academic format `STU_XXXX` (e.g., `STU_1001`).
3. **Enhancement Tables:**
   - `interventions`: Stores academic remedial actions proposed by faculty/admin. Statuses: `Open`, `In progress`, `Resolved`.
   - `audit_logs`: Stores immutable trace of critical operations (login, logout, student CRUD, prediction run, report export).
4. **Data Preservation:**
   - Existing 1,200 student records from `student_data.csv` and existing admin user (`ASMITA`) are preserved unconditionally.

---

## 4. Machine Learning & Explainability
1. **Target Leakage Prevention:**
   - Model inference features are strictly limited to the 8 pre-examination behavioral dimensions:
     - `attendance_rate`
     - `study_hours_per_week`
     - `previous_scores`
     - `assignment_completion_rate`
     - `tutoring_sessions`
     - `sleep_hours`
     - `extracurricular`
     - `internet_access`
   - Future outcomes (`final_exam_score`, `passed`) are strictly excluded from inference inputs.
2. **Explainability Logic:**
   - Local explanation is derived from the Logistic Regression coefficients and standardized Z-scores ($w_j \cdot z_j$).
   - The top 3 positive or negative contributors to the log-odds of passing are rendered in human-readable language.
3. **Decision Support Disclaimer:**
   - Predictions are advisory decision-support tools and do not constitute an official academic grading verdict.

---

## 5. What-If Simulation
- The interactive simulation tool allows teachers and students to experiment with input features (e.g. increasing study hours).
- Simulated runs are tagged as ephemeral simulations and are **never** committed to the `prediction_history` database table.
