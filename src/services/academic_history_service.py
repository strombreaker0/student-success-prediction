"""
Academic History Service.
Manages normalized Four-Year Academic Records, Semester Results,
Subject Results, and Student Activities/Achievements with strict RBAC enforcement.
"""

import io
import csv
import logging
from datetime import datetime, timezone
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from src.db.connection import get_db_connection
from src.services.auth_service import can_view_student, can_manage_students

logger = logging.getLogger(__name__)

YEAR_METADATA = {
    1: {"name": "First Year (FE)", "semesters": [1, 2]},
    2: {"name": "Second Year (SE)", "semesters": [3, 4]},
    3: {"name": "Third Year (TE)", "semesters": [5, 6]},
    4: {"name": "Final Year (BE)", "semesters": [7, 8]}
}

VALID_ACTIVITY_TYPES = [
    'Project', 'Extracurricular', 'Certificate',
    'Achievement', 'Internship', 'Workshop', 'Competition'
]

VALID_SEMESTER_STATUSES = ['Passed', 'Failed', 'In Progress', 'Pending', 'Not Recorded']
VALID_YEAR_STATUSES = ['Completed', 'In Progress', 'Not Started', 'On Hold']
VALID_SUBJECT_STATUSES = ['Pass', 'Fail', 'In Progress', 'Exempted']


def get_year_for_semester(semester_number: int) -> int:
    """Returns the academic year (1-4) corresponding to a semester (1-8)."""
    if 1 <= semester_number <= 2:
        return 1
    elif 3 <= semester_number <= 4:
        return 2
    elif 5 <= semester_number <= 6:
        return 3
    elif 7 <= semester_number <= 8:
        return 4
    raise ValueError(f"Invalid semester number {semester_number}. Must be between 1 and 8.")


def compute_grade_point(grade: str) -> float:
    """Maps standard letter grade to 10-point scale grade point."""
    mapping = {
        "O": 10.0,
        "A+": 9.0,
        "A": 8.0,
        "B+": 7.0,
        "B": 6.0,
        "C": 5.0,
        "P": 4.0,
        "F": 0.0
    }
    return mapping.get(str(grade).strip().upper(), 0.0)


def get_student_academic_history(
    student_id: str,
    requesting_user: dict | None = None,
    conn = None
) -> dict | None:
    """
    Retrieves the complete Four-Year Academic History for a student.
    Enforces RBAC: Students can ONLY access their own history.
    Returns structured data for Year 1 to Year 4, Semesters 1 to 8,
    Subjects, Activities, and Analytics.
    """
    clean_id = str(student_id).strip().upper()
    if requesting_user and not can_view_student(requesting_user, clean_id):
        return None

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()

        # 1. Base student record
        cursor.execute("SELECT * FROM students WHERE student_id = ?;", (clean_id,))
        student_row = cursor.fetchone()
        if not student_row:
            return None
        student_data = dict(student_row)

        # 2. Year records
        cursor.execute("""
        SELECT * FROM academic_year_records
        WHERE student_id = ?
        ORDER BY academic_year ASC;
        """, (clean_id,))
        year_rows = {r["academic_year"]: dict(r) for r in cursor.fetchall()}

        # 3. Semester results
        cursor.execute("""
        SELECT * FROM semester_results
        WHERE student_id = ?
        ORDER BY semester_number ASC;
        """, (clean_id,))
        sem_rows = {r["semester_number"]: dict(r) for r in cursor.fetchall()}

        # 4. Subject results
        cursor.execute("""
        SELECT sr.*, sem.semester_number
        FROM subject_results sr
        JOIN semester_results sem ON sr.semester_id = sem.id
        WHERE sr.student_id = ?
        ORDER BY sem.semester_number ASC, sr.subject_code ASC;
        """, (clean_id,))
        subjects_by_sem = {}
        for r in cursor.fetchall():
            s_dict = dict(r)
            s_num = s_dict["semester_number"]
            subjects_by_sem.setdefault(s_num, []).append(s_dict)

        # 5. Student activities
        cursor.execute("""
        SELECT * FROM student_activities
        WHERE student_id = ?
        ORDER BY academic_year ASC, semester_number ASC, id ASC;
        """, (clean_id,))
        activities = [dict(r) for r in cursor.fetchall()]

        # Build complete 4-Year & 8-Semester structure
        years_structured = []
        all_semesters_list = []
        total_credits_earned = 0.0
        total_credits_attempted = 0.0
        sgpa_list = []
        attendance_list = []
        assignment_list = []
        strengths = []
        improvement_areas = []

        for yr in range(1, 5):
            yr_meta = YEAR_METADATA[yr]
            yr_record = year_rows.get(yr, {
                "academic_year": yr,
                "year_name": yr_meta["name"],
                "academic_session": "Pending",
                "status": "Not Started",
                "cgpa": None,
                "attendance_rate": None,
                "total_credits_earned": 0.0,
                "remarks": ""
            })

            semesters_in_year = []
            for sem_num in yr_meta["semesters"]:
                sem_record = sem_rows.get(sem_num, {
                    "student_id": clean_id,
                    "academic_year": yr,
                    "semester_number": sem_num,
                    "semester_name": f"Semester {sem_num}",
                    "status": "Not Recorded",
                    "sgpa": None,
                    "total_credits": 0.0,
                    "credits_earned": 0.0,
                    "attendance_rate": None,
                    "assignment_completion_rate": None,
                    "remarks": ""
                })

                # Attach subjects
                subjs = subjects_by_sem.get(sem_num, [])
                sem_record["subjects"] = subjs
                semesters_in_year.append(sem_record)
                all_semesters_list.append(sem_record)

                # Compute aggregates if recorded
                if sem_record.get("status") in ("Passed", "Failed", "Completed"):
                    if sem_record.get("sgpa") is not None:
                        sgpa_list.append(sem_record["sgpa"])
                    total_credits_earned += float(sem_record.get("credits_earned") or 0.0)
                    total_credits_attempted += float(sem_record.get("total_credits") or 0.0)

                if sem_record.get("attendance_rate") is not None:
                    attendance_list.append(sem_record["attendance_rate"])
                    if sem_record["attendance_rate"] < 75.0:
                        improvement_areas.append(f"Semester {sem_num} Attendance Alert ({sem_record['attendance_rate']}%)")

                if sem_record.get("assignment_completion_rate") is not None:
                    assignment_list.append(sem_record["assignment_completion_rate"])
                    if sem_record["assignment_completion_rate"] < 75.0:
                        improvement_areas.append(f"Semester {sem_num} Assignment Submission Deficit ({sem_record['assignment_completion_rate']}%)")

                # Parse subject strengths / improvement areas
                for s in subjs:
                    g = str(s.get("grade", "")).strip().upper()
                    m = s.get("total_marks")
                    if g in ("O", "A+", "A") or (m is not None and m >= 75.0):
                        strengths.append(f"Excellence in {s['subject_name']} ({s['subject_code']}) - Grade: {g or 'A'}")
                    elif g in ("F", "C", "P") or (m is not None and m < 50.0):
                        improvement_areas.append(f"Subject Deficit: {s['subject_name']} ({s['subject_code']}) - Grade: {g or 'Low Marks'}")

            yr_record["semesters"] = semesters_in_year
            years_structured.append(yr_record)

        # Overall CGPA
        overall_cgpa = round(sum(sgpa_list) / len(sgpa_list), 2) if sgpa_list else None
        overall_attendance = round(sum(attendance_list) / len(attendance_list), 1) if attendance_list else None
        overall_assignment = round(sum(assignment_list) / len(assignment_list), 1) if assignment_list else None

        # Current standing determination
        recorded_sems = [s for s in all_semesters_list if s.get("status") != "Not Recorded"]
        if recorded_sems:
            latest_sem = max(s["semester_number"] for s in recorded_sems)
            current_standing = f"Year {get_year_for_semester(latest_sem)} (Semester {latest_sem})"
        else:
            current_standing = "Year 1 (Semester 1 - Not Recorded)"

        # Generate constructive recommendations
        recommendations = []
        if overall_cgpa is not None:
            if overall_cgpa >= 8.5:
                recommendations.append("High Academic Distinction: Target honors track, academic publications, and competitive national examinations.")
            elif overall_cgpa >= 7.0:
                recommendations.append("Solid Consistent Performance: Focus on higher grade conversions in specialized elective subjects.")
            else:
                recommendations.append("Academic Elevation Required: Schedule concept revision sessions with mentors to raise overall CGPA above 7.0.")

        if overall_attendance is not None and overall_attendance < 75.0:
            recommendations.append(f"Statutory Attendance Warning: Cumulative attendance is {overall_attendance}%. Attendance must be brought to ≥ 75% to maintain examination eligibility.")

        if not recommendations:
            recommendations.append("Maintain disciplined attendance and submit coursework ahead of deadlines.")

        return {
            "student": student_data,
            "years": years_structured,
            "all_semesters": all_semesters_list,
            "activities": activities,
            "analytics": {
                "current_standing": current_standing,
                "overall_cgpa": overall_cgpa,
                "overall_attendance": overall_attendance,
                "overall_assignment": overall_assignment,
                "total_credits_earned": total_credits_earned,
                "total_credits_attempted": total_credits_attempted,
                "completed_semesters_count": len([s for s in all_semesters_list if s.get("status") == "Passed"]),
                "strengths": strengths[:6],
                "improvement_areas": improvement_areas[:6],
                "recommendations": recommendations
            }
        }
    finally:
        if close_conn:
            conn.close()


def upsert_semester_record(
    student_id: str,
    semester_number: int,
    status: str = "Passed",
    sgpa: float = None,
    total_credits: float = 20.0,
    credits_earned: float = 20.0,
    attendance_rate: float = 85.0,
    assignment_rate: float = 85.0,
    remarks: str = "",
    academic_session: str = "2023-2024",
    requesting_user: dict | None = None,
    conn = None
) -> tuple[bool, str, dict | None]:
    """
    Creates or updates a semester result entry for a student.
    Requires Admin or Faculty permission.
    """
    if requesting_user and not can_manage_students(requesting_user):
        return False, "Permission denied: Only Admin or Faculty can enter academic records.", None

    clean_id = str(student_id).strip().upper()
    if not (1 <= semester_number <= 8):
        return False, f"Invalid semester number {semester_number}. Must be between 1 and 8.", None

    academic_year = get_year_for_semester(semester_number)

    if status not in VALID_SEMESTER_STATUSES:
        return False, f"Invalid status: {status}. Must be one of: {', '.join(VALID_SEMESTER_STATUSES)}", None

    if sgpa is not None and not (0.0 <= sgpa <= 10.0):
        return False, f"SGPA must be between 0.0 and 10.0 (received {sgpa}).", None

    if attendance_rate is not None and not (0.0 <= attendance_rate <= 100.0):
        return False, "Attendance rate must be between 0.0 and 100.0%.", None

    if assignment_rate is not None and not (0.0 <= assignment_rate <= 100.0):
        return False, "Assignment completion rate must be between 0.0 and 100.0%.", None

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()

        # Check student exists
        cursor.execute("SELECT student_id FROM students WHERE student_id = ?;", (clean_id,))
        if not cursor.fetchone():
            return False, f"Student '{clean_id}' does not exist.", None

        now = datetime.now(timezone.utc).isoformat()
        sem_name = f"Semester {semester_number}"

        # 1. Upsert Semester Result
        cursor.execute("""
        INSERT INTO semester_results (
            student_id, academic_year, semester_number, semester_name,
            status, sgpa, total_credits, credits_earned,
            attendance_rate, assignment_completion_rate, remarks,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id, semester_number) DO UPDATE SET
            status = excluded.status,
            sgpa = excluded.sgpa,
            total_credits = excluded.total_credits,
            credits_earned = excluded.credits_earned,
            attendance_rate = excluded.attendance_rate,
            assignment_completion_rate = excluded.assignment_completion_rate,
            remarks = excluded.remarks,
            updated_at = excluded.updated_at;
        """, (
            clean_id, academic_year, semester_number, sem_name,
            status, sgpa, total_credits, credits_earned,
            attendance_rate, assignment_rate, remarks,
            now, now
        ))

        # 2. Sync/Upsert Parent Academic Year Record
        year_name = YEAR_METADATA[academic_year]["name"]
        cursor.execute("""
        INSERT INTO academic_year_records (
            student_id, academic_year, year_name, academic_session,
            status, cgpa, attendance_rate, total_credits_earned,
            remarks, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id, academic_year) DO UPDATE SET
            academic_session = excluded.academic_session,
            updated_at = excluded.updated_at;
        """, (
            clean_id, academic_year, year_name, academic_session,
            "In Progress" if status != "Passed" else "Completed",
            sgpa, attendance_rate, credits_earned,
            remarks, now, now
        ))

        conn.commit()

        # Fetch created/updated semester record
        cursor.execute("""
        SELECT * FROM semester_results
        WHERE student_id = ? AND semester_number = ?;
        """, (clean_id, semester_number))
        saved = dict(cursor.fetchone())

        return True, f"Semester {semester_number} record saved successfully.", saved
    except Exception as e:
        return False, f"Database error saving semester record: {e}", None
    finally:
        if close_conn:
            conn.close()


def add_subject_result(
    student_id: str,
    semester_number: int,
    subject_code: str,
    subject_name: str,
    credits: float = 3.0,
    internal_marks: float = 20.0,
    external_marks: float = 60.0,
    total_marks: float = 80.0,
    max_marks: float = 100.0,
    grade: str = "A",
    status: str = "Pass",
    requesting_user: dict | None = None,
    conn = None
) -> tuple[bool, str, dict | None]:
    """Adds a subject result to a semester. Creates semester stub if not already existing."""
    if requesting_user and not can_manage_students(requesting_user):
        return False, "Permission denied: Only Admin or Faculty can enter subject results.", None

    clean_id = str(student_id).strip().upper()
    clean_code = str(subject_code).strip().upper()
    clean_name = str(subject_name).strip()

    if not clean_code or not clean_name:
        return False, "Subject code and subject name are required.", None

    if credits <= 0.0:
        return False, "Credits must be greater than zero.", None

    if total_marks is None and internal_marks is not None and external_marks is not None:
        total_marks = internal_marks + external_marks

    grade_point = compute_grade_point(grade)

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()

        # Ensure semester_results record exists
        cursor.execute("""
        SELECT id FROM semester_results
        WHERE student_id = ? AND semester_number = ?;
        """, (clean_id, semester_number))
        sem_row = cursor.fetchone()

        if not sem_row:
            # Auto-create semester entry
            ok_sem, msg_sem, sem_rec = upsert_semester_record(
                student_id=clean_id,
                semester_number=semester_number,
                status="In Progress",
                requesting_user=requesting_user,
                conn=conn
            )
            if not ok_sem:
                return False, f"Could not create parent semester: {msg_sem}", None
            semester_id = sem_rec["id"]
        else:
            semester_id = sem_row["id"]

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        INSERT INTO subject_results (
            semester_id, student_id, subject_code, subject_name,
            credits, internal_marks, external_marks, total_marks,
            max_marks, grade, grade_point, status,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(semester_id, subject_code) DO UPDATE SET
            subject_name = excluded.subject_name,
            credits = excluded.credits,
            internal_marks = excluded.internal_marks,
            external_marks = excluded.external_marks,
            total_marks = excluded.total_marks,
            max_marks = excluded.max_marks,
            grade = excluded.grade,
            grade_point = excluded.grade_point,
            status = excluded.status,
            updated_at = excluded.updated_at;
        """, (
            semester_id, clean_id, clean_code, clean_name,
            credits, internal_marks, external_marks, total_marks,
            max_marks, grade.upper(), grade_point, status,
            now, now
        ))
        conn.commit()

        cursor.execute("SELECT * FROM subject_results WHERE semester_id = ? AND subject_code = ?;", (semester_id, clean_code))
        saved = dict(cursor.fetchone())
        return True, f"Subject '{clean_code}: {clean_name}' recorded successfully.", saved
    except Exception as e:
        return False, f"Error saving subject result: {e}", None
    finally:
        if close_conn:
            conn.close()


def delete_subject_result(subject_id: int, requesting_user: dict | None = None, conn = None) -> tuple[bool, str]:
    """Deletes a subject result."""
    if requesting_user and not can_manage_students(requesting_user):
        return False, "Permission denied: Only Admin or Faculty can remove subject results."

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subject_results WHERE id = ?;", (subject_id,))
        conn.commit()
        return True, "Subject result deleted successfully."
    except Exception as e:
        return False, f"Error deleting subject: {e}"
    finally:
        if close_conn:
            conn.close()


def add_student_activity(
    student_id: str,
    activity_type: str,
    title: str,
    description: str = "",
    organization_or_issuer: str = "",
    date_or_period: str = "",
    outcome_or_award: str = "",
    academic_year: int = 1,
    semester_number: int = 1,
    skills_acquired: str = "",
    requesting_user: dict | None = None,
    conn = None
) -> tuple[bool, str, dict | None]:
    """Adds a student project, certificate, extracurricular, or achievement."""
    if requesting_user and not can_manage_students(requesting_user):
        return False, "Permission denied: Only Admin or Faculty can record activities.", None

    clean_id = str(student_id).strip().upper()
    if activity_type not in VALID_ACTIVITY_TYPES:
        return False, f"Invalid activity type: {activity_type}. Must be one of: {', '.join(VALID_ACTIVITY_TYPES)}", None

    if not title or not title.strip():
        return False, "Activity title is required.", None

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        INSERT INTO student_activities (
            student_id, academic_year, semester_number, activity_type,
            title, description, organization_or_issuer, date_or_period,
            outcome_or_award, skills_acquired, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            clean_id, academic_year, semester_number, activity_type,
            title.strip(), description.strip(), organization_or_issuer.strip(),
            date_or_period.strip(), outcome_or_award.strip(), skills_acquired.strip(),
            now
        ))
        conn.commit()
        act_id = cursor.lastrowid
        cursor.execute("SELECT * FROM student_activities WHERE id = ?;", (act_id,))
        saved = dict(cursor.fetchone())
        return True, f"{activity_type} '{title.strip()}' recorded successfully.", saved
    except Exception as e:
        return False, f"Error saving activity: {e}", None
    finally:
        if close_conn:
            conn.close()


def delete_student_activity(activity_id: int, requesting_user: dict | None = None, conn = None) -> tuple[bool, str]:
    """Deletes a student activity record."""
    if requesting_user and not can_manage_students(requesting_user):
        return False, "Permission denied: Only Admin or Faculty can remove activities."

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM student_activities WHERE id = ?;", (activity_id,))
        conn.commit()
        return True, "Activity record removed successfully."
    except Exception as e:
        return False, f"Error deleting activity: {e}"
    finally:
        if close_conn:
            conn.close()


# ---------------- Transcript & Report Exports ----------------

def export_academic_transcript_csv(student_id: str, requesting_user: dict | None = None, conn = None) -> str:
    """Exports the 4-year semester and subject breakdown as a CSV transcript."""
    history = get_student_academic_history(student_id, requesting_user=requesting_user, conn=conn)
    if not history:
        return ""

    rows = []
    student = history["student"]

    for yr in history["years"]:
        yr_num = yr["academic_year"]
        yr_name = yr["year_name"]
        for sem in yr["semesters"]:
            sem_num = sem["semester_number"]
            sem_status = sem["status"]
            sgpa = sem["sgpa"]
            att = sem["attendance_rate"]
            assign = sem["assignment_completion_rate"]

            subjects = sem.get("subjects", [])
            if not subjects:
                rows.append({
                    "Student_ID": student["student_id"],
                    "Academic_Year": yr_name,
                    "Semester": f"Semester {sem_num}",
                    "Semester_Status": sem_status,
                    "SGPA": sgpa,
                    "Semester_Attendance_%": att,
                    "Semester_Assignments_%": assign,
                    "Subject_Code": "N/A",
                    "Subject_Name": "No subjects recorded",
                    "Credits": 0,
                    "Total_Marks": "",
                    "Grade": "",
                    "Subject_Status": ""
                })
            else:
                for subj in subjects:
                    rows.append({
                        "Student_ID": student["student_id"],
                        "Academic_Year": yr_name,
                        "Semester": f"Semester {sem_num}",
                        "Semester_Status": sem_status,
                        "SGPA": sgpa,
                        "Semester_Attendance_%": att,
                        "Semester_Assignments_%": assign,
                        "Subject_Code": subj["subject_code"],
                        "Subject_Name": subj["subject_name"],
                        "Credits": subj["credits"],
                        "Total_Marks": subj["total_marks"],
                        "Grade": subj["grade"],
                        "Subject_Status": subj["status"]
                    })

    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def generate_academic_transcript_pdf(student_id: str, requesting_user: dict | None = None, conn = None) -> bytes:
    """Generates an official-looking, publication-ready PDF academic transcript using ReportLab."""
    history = get_student_academic_history(student_id, requesting_user=requesting_user, conn=conn)
    if not history:
        return b""

    student = history["student"]
    analytics = history["analytics"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        alignment=1
    )
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    table_cell_style = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0f172a')
    )
    table_header_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    story = []

    # Title & Header
    story.append(Paragraph("INSTITUTIONAL ACADEMIC PROGRESS TRANSCRIPT", title_style))
    story.append(Paragraph("Department of Computer Science & Engineering | Academic Lifecycle Record", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceBefore=2, spaceAfter=10))

    # Student Profile Summary Box
    info_data = [
        [
            Paragraph(f"<b>Student ID:</b> {student['student_id']}", body_style),
            Paragraph(f"<b>Current Standing:</b> {analytics['current_standing']}", body_style),
            Paragraph(f"<b>Cumulative CGPA:</b> {analytics['overall_cgpa'] or 'N/A'}", body_style)
        ],
        [
            Paragraph(f"<b>Credits Earned:</b> {analytics['total_credits_earned']}", body_style),
            Paragraph(f"<b>Avg Attendance:</b> {analytics['overall_attendance'] or 'N/A'}%", body_style),
            Paragraph(f"<b>Semesters Completed:</b> {analytics['completed_semesters_count']} of 8", body_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[180, 180, 180])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 14))

    # Four Years Breakdown
    story.append(Paragraph("Four-Year Semester Performance Breakdown", h2_style))

    table_data = [
        [
            Paragraph("Year", table_header_style),
            Paragraph("Semester", table_header_style),
            Paragraph("Status", table_header_style),
            Paragraph("SGPA", table_header_style),
            Paragraph("Credits", table_header_style),
            Paragraph("Attendance", table_header_style),
            Paragraph("Subjects Recorded", table_header_style)
        ]
    ]

    for yr in history["years"]:
        yr_name = yr["year_name"].split(" ")[0] + " Year"
        for sem in yr["semesters"]:
            subjs_count = len(sem.get("subjects", []))
            table_data.append([
                Paragraph(yr_name, table_cell_style),
                Paragraph(f"Sem {sem['semester_number']}", table_cell_style),
                Paragraph(sem["status"], table_cell_style),
                Paragraph(str(sem["sgpa"] if sem["sgpa"] is not None else "-"), table_cell_style),
                Paragraph(f"{sem['credits_earned']}/{sem['total_credits']}", table_cell_style),
                Paragraph(f"{sem['attendance_rate']}%" if sem['attendance_rate'] is not None else "-", table_cell_style),
                Paragraph(f"{subjs_count} Subject(s)", table_cell_style)
            ])

    sem_table = Table(table_data, colWidths=[80, 65, 85, 55, 65, 80, 110])
    sem_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sem_table)
    story.append(Spacer(1, 14))

    # Activities & Achievements Section
    if history.get("activities"):
        story.append(Paragraph("Projects, Certifications & Achievements", h2_style))
        act_data = [
            [
                Paragraph("Type", table_header_style),
                Paragraph("Title", table_header_style),
                Paragraph("Organization / Period", table_header_style),
                Paragraph("Outcome / Award", table_header_style)
            ]
        ]
        for a in history["activities"][:8]:
            act_data.append([
                Paragraph(a.get("activity_type", ""), table_cell_style),
                Paragraph(a.get("title", ""), table_cell_style),
                Paragraph(f"{a.get('organization_or_issuer', '')} ({a.get('date_or_period', '')})", table_cell_style),
                Paragraph(a.get("outcome_or_award", ""), table_cell_style)
            ])

        act_table = Table(act_data, colWidths=[90, 180, 140, 130])
        act_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(act_table)
        story.append(Spacer(1, 14))

    # Footer Notice
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#cbd5e1'), spaceBefore=8, spaceAfter=6))
    notice_text = "This transcript is generated automatically by the Student Academic Success Prediction System. Candidate: Asmita Chandram Kumbar (SYBSc CS, Roll No: SI1161)."
    story.append(Paragraph(notice_text, subtitle_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
