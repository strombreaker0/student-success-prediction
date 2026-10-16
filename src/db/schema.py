"""
Database schema definition and table initialization.
Enforces constraints, foreign keys, and indexes for data integrity.
Allows nullable features to faithfully preserve raw dataset records with missing values.
Includes full Four-Year Academic History tables:
- academic_year_records
- semester_results
- subject_results
- student_activities
"""

def create_schema(conn):
    """
    Creates necessary tables and indexes if they do not exist.
    """
    cursor = conn.cursor()

    # 1. Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        attendance_rate REAL CHECK(attendance_rate IS NULL OR (attendance_rate >= 0.0 AND attendance_rate <= 100.0)),
        study_hours_per_week REAL CHECK(study_hours_per_week IS NULL OR (study_hours_per_week >= 0.0 AND study_hours_per_week <= 168.0)),
        previous_scores REAL CHECK(previous_scores IS NULL OR (previous_scores >= 0.0 AND previous_scores <= 100.0)),
        assignment_completion_rate REAL CHECK(assignment_completion_rate IS NULL OR (assignment_completion_rate >= 0.0 AND assignment_completion_rate <= 100.0)),
        tutoring_sessions INTEGER CHECK(tutoring_sessions IS NULL OR (tutoring_sessions >= 0 AND tutoring_sessions <= 50)),
        sleep_hours REAL CHECK(sleep_hours IS NULL OR (sleep_hours >= 0.0 AND sleep_hours <= 24.0)),
        extracurricular INTEGER CHECK(extracurricular IS NULL OR extracurricular IN (0, 1)),
        internet_access INTEGER CHECK(internet_access IS NULL OR internet_access IN (0, 1)),
        final_exam_score REAL CHECK(final_exam_score IS NULL OR (final_exam_score >= 0.0 AND final_exam_score <= 100.0)),
        passed INTEGER CHECK(passed IS NULL OR passed IN (0, 1)),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL COLLATE NOCASE,
        email TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'faculty', 'student')),
        linked_student_id TEXT REFERENCES students(student_id) ON DELETE SET NULL,
        full_name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Prediction History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prediction_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
        model_name TEXT NOT NULL,
        predicted_outcome INTEGER NOT NULL CHECK(predicted_outcome IN (0, 1)),
        pass_probability REAL NOT NULL CHECK(pass_probability >= 0.0 AND pass_probability <= 1.0),
        fail_probability REAL NOT NULL CHECK(fail_probability >= 0.0 AND fail_probability <= 1.0),
        risk_category TEXT NOT NULL CHECK(risk_category IN ('Low Risk', 'Moderate Risk', 'High Risk')),
        interventions_json TEXT NOT NULL,
        top_factors_json TEXT,
        predicted_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Four-Year Academic Year Records Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS academic_year_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
        academic_year INTEGER NOT NULL CHECK(academic_year BETWEEN 1 AND 4),
        year_name TEXT NOT NULL,
        academic_session TEXT,
        status TEXT NOT NULL DEFAULT 'Not Started' CHECK(status IN ('Completed', 'In Progress', 'Not Started', 'On Hold')),
        cgpa REAL CHECK(cgpa IS NULL OR (cgpa >= 0.0 AND cgpa <= 10.0)),
        attendance_rate REAL CHECK(attendance_rate IS NULL OR (attendance_rate >= 0.0 AND attendance_rate <= 100.0)),
        total_credits_earned REAL DEFAULT 0.0 CHECK(total_credits_earned >= 0.0),
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, academic_year)
    );
    """)

    # 5. Semester Results Table (Semesters 1 through 8)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS semester_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
        academic_year INTEGER NOT NULL CHECK(academic_year BETWEEN 1 AND 4),
        semester_number INTEGER NOT NULL CHECK(semester_number BETWEEN 1 AND 8),
        semester_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Not Recorded' CHECK(status IN ('Passed', 'Failed', 'In Progress', 'Pending', 'Not Recorded')),
        sgpa REAL CHECK(sgpa IS NULL OR (sgpa >= 0.0 AND sgpa <= 10.0)),
        total_credits REAL DEFAULT 0.0 CHECK(total_credits >= 0.0),
        credits_earned REAL DEFAULT 0.0 CHECK(credits_earned >= 0.0),
        attendance_rate REAL CHECK(attendance_rate IS NULL OR (attendance_rate >= 0.0 AND attendance_rate <= 100.0)),
        assignment_completion_rate REAL CHECK(assignment_completion_rate IS NULL OR (assignment_completion_rate >= 0.0 AND assignment_completion_rate <= 100.0)),
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, semester_number)
    );
    """)

    # 6. Subject Results Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subject_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester_id INTEGER NOT NULL REFERENCES semester_results(id) ON DELETE CASCADE,
        student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
        subject_code TEXT NOT NULL,
        subject_name TEXT NOT NULL,
        credits REAL NOT NULL DEFAULT 3.0 CHECK(credits > 0.0),
        internal_marks REAL CHECK(internal_marks IS NULL OR (internal_marks >= 0.0 AND internal_marks <= 100.0)),
        external_marks REAL CHECK(external_marks IS NULL OR (external_marks >= 0.0 AND external_marks <= 100.0)),
        total_marks REAL CHECK(total_marks IS NULL OR (total_marks >= 0.0 AND total_marks <= 100.0)),
        max_marks REAL NOT NULL DEFAULT 100.0 CHECK(max_marks > 0.0),
        grade TEXT,
        grade_point REAL CHECK(grade_point IS NULL OR (grade_point >= 0.0 AND grade_point <= 10.0)),
        status TEXT NOT NULL DEFAULT 'In Progress' CHECK(status IN ('Pass', 'Fail', 'In Progress', 'Exempted')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(semester_id, subject_code)
    );
    """)

    # 7. Student Activities, Projects & Achievements Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
        academic_year INTEGER CHECK(academic_year IS NULL OR academic_year BETWEEN 1 AND 4),
        semester_number INTEGER CHECK(semester_number IS NULL OR semester_number BETWEEN 1 AND 8),
        activity_type TEXT NOT NULL CHECK(activity_type IN ('Project', 'Extracurricular', 'Certificate', 'Achievement', 'Internship', 'Workshop', 'Competition')),
        title TEXT NOT NULL,
        description TEXT,
        organization_or_issuer TEXT,
        date_or_period TEXT,
        outcome_or_award TEXT,
        skills_acquired TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 8. Interventions Tracker Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'In progress', 'Resolved')),
        follow_up_date TEXT,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 9. Audit Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        target TEXT,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 10. Indexes for optimal query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_passed ON students(passed);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_student ON prediction_history(student_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_created ON prediction_history(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_acad_student ON academic_year_records(student_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sem_student ON semester_results(student_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subj_semester ON subject_results(semester_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subj_student ON subject_results(student_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_student ON student_activities(student_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interventions_student_id ON interventions(student_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interventions_status ON interventions(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);")

    conn.commit()
