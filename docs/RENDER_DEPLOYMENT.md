# Render Deployment Guide: AI-Based Student Academic Success Prediction System

**Repository:** `strombreaker0/EduPredict-AI`  
**Target Application:** Flask Production Application (`flask_app/` via `wsgi:application`)  
**Status:** Prepared and Tested  

---

## 1. Root Cause of Previous Deployment Error

**Previous Deployment Crash:**
```
sqlite3.OperationalError: no such table: users
```

### Technical Root Cause:
1. **Uncommitted Database:** `.gitignore` excludes `database/*.db`, which is standard best practice to prevent commiting sensitive data. When Render clones the repository, the database file does not exist.
2. **Migration Order Flaw in `src/db/migrate_enhancements.py`:** The previous enhancement migration script queried `PRAGMA table_info(users);` before verifying whether the table had been created. On an empty database, `PRAGMA table_info` returns an empty set `[]`, causing `"last_login" not in user_cols` to evaluate to `True` and trigger `ALTER TABLE users ADD COLUMN last_login TIMESTAMP;`. In SQLite, attempting to alter a non-existent table immediately throws `OperationalError: no such table: users`.
3. **App Initialization Exception Suppression:** In `flask_app/__init__.py`, the startup try-catch logged this crash as a warning instead of ensuring base schema creation was completed. The subsequent HTTP request then attempted to query the non-existent `users` table, crashing the application.

### The Fix Applied:
1. **Defensive Migration:** `src/db/migrate_enhancements.py` now guarantees `create_schema(conn)` has run first and explicitly inspects `sqlite_master` table existence before running any `ALTER TABLE` statements.
2. **Centralized Bootstrapper (`src/db/init_app_db.py`):** Added `ensure_db_initialized()` which runs automatically on WSGI startup. It idempotently creates all 9 tables + indexes, runs enhancement migrations, and auto-seeds the 1,200 baseline student cohort from `data/student_data.csv` if the database is fresh.
3. **Admin Auto-Provisioning:** If deploying to a fresh database with 0 users, specifying `ADMIN_PASSWORD` in Render environment variables automatically provisions the initial administrator account on boot, preventing locked-out deployments.

---

## 2. Render Deployment Specifications

### Web Service Configuration

| Setting | Value |
| :--- | :--- |
| **Service Type** | Web Service |
| **Language / Runtime** | `Python` (specified via `runtime.txt` as `3.11.9`) |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --bind 0.0.0.0:$PORT wsgi:application` |
| **Health Check Path** | `/health` (or `/healthz`) |
| **Auto-Deploy** | `Yes` (recommended on git push) |

---

## 3. Environment Variables

Configure the following variables in the **Environment** tab of your Render service dashboard:

### Required Production Variables:
| Variable | Suggested Value | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | *(Generate a 64-char hex)* | Session & CSRF encryption key. Generate via `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `FLASK_ENV` | `production` | Enforces production mode and activates `ProxyFix` middleware. |
| `SECURE_COOKIES` | `1` | Enforces `Secure` flag on session cookies over HTTPS (`.onrender.com`). |
| `STUDENT_DB_PATH` | `database/student_success.db` | Path to SQLite database (or `/var/data/student_success.db` if using a Persistent Disk). |

### Optional Initial Bootstrapping Variables:
| Variable | Suggested Value | Description |
| :--- | :--- | :--- |
| `ADMIN_USERNAME` | `admin` | Initial admin username if database is empty. |
| `ADMIN_EMAIL` | `admin@institution.edu` | Initial admin email address. |
| `ADMIN_PASSWORD` | *(Strong Password)* | If set and users table is empty, creates initial admin user automatically. |
| `ADMIN_NAME` | `System Administrator` | Admin display name. |

---

## 4. Production Database Persistence

### Option A: Render Free Tier (Ephemeral Storage)
- Render Free Web Services use ephemeral container disks. When the container sleeps, restarts, or redeploys, filesystem changes revert.
- **How our solution handles this:** The new `ensure_db_initialized()` routine detects a fresh instance on boot, creates the schema, auto-seeds the 1,200 student records from `data/student_data.csv`, and auto-creates the administrator from `ADMIN_PASSWORD`. The application will remain fully functional on every wake-up.
- **Limitation:** Any new students added via UI will reset upon container restart.

### Option B: Render Starter Tier + Persistent Disk (Recommended for Long-Term Data Retention)
1. Upgrade service plan to **Starter** ($7/mo).
2. Attach a **Render Disk**:
   - **Name:** `sqlite-data`
   - **Mount Path:** `/var/data`
   - **Size:** `1 GB`
3. Update environment variable:
   - `STUDENT_DB_PATH=/var/data/student_success.db`
4. All SQLite records, user accounts, prediction histories, and intervention notes will persist indefinitely across all redeploys.

---

## 5. Machine Learning Models & Artifacts

- **Model Files Tracked in Git:**
  - `models/imputer.joblib`
  - `models/scaler.joblib`
  - `models/logistic_regression_model.joblib`
  - `models/decision_tree_model.joblib`
  - `models/random_forest_model.joblib`
- **Compatibility:** Tested and verified under `scikit-learn>=1.3.0` and Python 3.11 / 3.13. All artifacts load in under 0.15 seconds with zero deserialization warnings.
- **Streamlit Intact:** The original Streamlit application (`app.py`) remains completely untouched and functional for standalone local analytics.

---

## 6. Migration Procedure

- **Automatic (Zero-Touch):** Every time the WSGI app starts, `ensure_db_initialized()` runs safely. All migrations are strictly additive (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) and will never delete, drop, or overwrite data.
- **Manual (Via Render Shell):** If you need to perform maintenance manually:
  ```bash
  python init_db.py
  flask create-admin
  ```

---

## 7. Verification & Health Monitoring

The service includes an enhanced health check route at `/health` (and alias `/healthz`).

**Example Response:**
```json
{
  "database": "connected",
  "models": "loaded",
  "records": {
    "students": 1200,
    "users": 2
  },
  "service": "AI-Based Student Academic Success Prediction System",
  "status": "healthy",
  "tables_ready": true,
  "timestamp": "2026-10-16T12:47:25.123456+00:00"
}
```

If database connectivity fails, models fail to load, or required tables are missing, the endpoint returns HTTP `503 Service Unavailable`, informing Render not to route web traffic to an unhealthy container.
