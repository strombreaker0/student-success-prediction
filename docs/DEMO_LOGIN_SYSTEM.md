# Demo Login System Documentation

**Project:** AI-Based Student Academic Success Prediction System  
**Feature:** Instant Dual-Persona Demo Login (`Admin Demo` & `Student Demo`)  
**Status:** Implemented, Tested (76 passed tests), Production Ready  

---

## 1. Overview & Architecture

The Demo Login System enables prospective reviewers, academic evaluators, and stakeholders to immediately evaluate both system perspectives without needing to perform manual account registration or remember separate credentials:

1. **Continue as Admin Demo**: Authenticates as an authorized institutional administrator/faculty user, granting full visibility over executive cohort KPIs, at-risk rosters, batch CSV screening, machine learning model transparency, and student CRUD actions.
2. **Continue as Student Demo**: Authenticates as an enrolled student linked to dedicated synthetic profile `STU_DEMO01`, granting self-service access to individual GPA trajectory, 4-year academic transcript, ML success probability, and personalized interventions while strictly blocking all administrative functions and peers' profiles.

### Security-First Architecture
* **Real Backend Authentication**: When a demo button is clicked, a standard `POST /demo-login` request is dispatched with valid Flask-WTF CSRF tokens. The backend retrieves the demo persona credentials from server environment/configuration and executes the full PBKDF2/SHA-256 password hash verification against the database.
* **No Frontend Role Forgery**: No roles or permissions are set in the client or session. User role and permissions originate solely from the authenticated database record via Flask-Login (`login_user(user)`).
* **Session Fixation Defense**: Existing sessions are invalidated and regenerated (`session.clear()`) upon login.
* **Brute-Force & Rate Limiting**: The demo endpoints participate in the application's sliding-window rate limiter (`is_rate_limited`).
* **IDOR Prevention**: Student accounts can view only records matching `current_user.linked_student_id`. Attempts to access peer records (e.g. `/students/STU_1001`) or peer PDF reports result in HTTP `403 Forbidden`.
* **Zero Real Data Exposure**: The student demo account is linked strictly to a synthetic profile (`STU_DEMO01`), preventing leakage of baseline cohort records.

---

## 2. Demo Personas & Credentials

| Persona | Role | Default Username | Default Password | Linked Student ID | Permitted Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Admin Demo** | `admin` | `demo_admin` | `DemoAdmin#2026!` | `None` | Executive Dashboard, All Students, Batch ML Screening, Interventions, Audit Trail, Model Transparency |
| **Student Demo** | `student` | `demo_student` | `DemoStudent#2026!` | `STU_DEMO01` | Personal Dashboard/Profile (`/students/STU_DEMO01`), Academic Trajectory, Own PDF Report |

> **Security Note:** Passwords comply with password complexity rules (length >= 8, digits + letters) and are stored exclusively as PBKDF2/SHA-256 hashes. Plaintext passwords are never displayed in HTML, logs, or API responses.

---

## 3. Account Provisioning Instructions

Demo accounts are provisioned via explicit execution (not created automatically on every application boot to prevent unwanted public accounts).

### A. Local Execution (PowerShell / Command Prompt)

**Option 1: Using Standalone Script**
```powershell
python create_demo_accounts.py
```

**Option 2: Using Custom Passwords**
```powershell
python create_demo_accounts.py --admin-password "MySecretAdmin#2026!" --student-password "MySecretStudent#2026!"
```

**Option 3: Using Interactive Hidden Prompt**
```powershell
python create_demo_accounts.py --interactive
```

**Option 4: Using Flask CLI**
```powershell
flask create-demo-accounts
```

### B. Render Cloud Configuration

To make demo accounts available on Render, you have two options:

#### Option 1: Automatic Provisioning in Render Build Command (Recommended)
In the Render Web Service settings, update the **Build Command**:
```bash
pip install -r requirements.txt && python create_demo_accounts.py
```
This runs the idempotent script during deployment. If the accounts already exist, it synchronizes them without resetting existing database data.

#### Option 2: Run via Render Shell Console
Open your Render Web Service dashboard, navigate to the **Shell** tab, and run:
```bash
python create_demo_accounts.py
```

#### Optional Render Environment Variables
To customize demo credentials on Render, set:
* `DEMO_ADMIN_PASSWORD`: Custom secure password for demo admin
* `DEMO_STUDENT_PASSWORD`: Custom secure password for demo student

---

## 4. Demo Login Flow (User Experience)

1. Navigate to `/login`.
2. Below the primary sign-in form, the page presents two styled persona cards:
   * **Continue as Admin Demo** (Indigo shield icon)
   * **Continue as Student Demo** (Teal person badge icon)
3. Clicking either card submits an encrypted POST request to `/demo-login`.
4. The server validates the CSRF token and executes `authenticate_user()`.
5. Upon successful authentication:
   * **Admin Demo**: Redirected to `/dashboard` with full executive analytics.
   * **Student Demo**: Redirected to `/dashboard`, which automatically routes them to their personalized profile at `/students/STU_DEMO01`.
6. Clicking **Sign Out** clears the session, invalidates cookies, and returns the user to the login screen.

---

## 5. Automated Verification & Test Results

The test suite in [`tests/test_demo_login_system.py`](file:///c:/Users/Pruthviraj/Downloads/student_success_prediction/tests/test_demo_login_system.py) verifies:
1. `test_01_admin_demo_login_succeeds`: Validates server-side login and executive dashboard rendering.
2. `test_02_student_demo_login_succeeds`: Validates server-side student login and routing to `STU_DEMO01`.
3. `test_03_invalid_demo_role_and_credentials_rejected`: Verifies rejection of tampered roles or invalid passwords.
4. `test_04_admin_only_pages_reject_student_demo`: Verifies that `/students/new`, `/bulk-upload`, `/export`, `/audit`, and `/transparency` return HTTP `403 Forbidden` for student demo.
5. `test_05_students_cannot_access_other_students_records`: Verifies IDOR defense against peer records and peer PDF generation.
6. `test_06_logout_clears_session`: Verifies session invalidation and redirect on subsequent protected requests.
7. `test_07_rerunning_provisioning_is_idempotent`: Verifies repeated runs do not create duplicate accounts or alter existing user records.
8. `test_08_unprovisioned_demo_account_returns_helpful_message`: Verifies graceful notice if demo account is unprovisioned.
9. `test_09_csrf_protection_enforced_on_demo_login`: Verifies CSRF rejection (HTTP `400`) if token is missing.

**Full Test Suite Result:** `76 passed in 114.44s`
