"""
PDF Report Generation Service using ReportLab.
Produces a comprehensive academic assessment dossier including student metrics,
latest predictive risk assessment, top explainable factors, and remediation plan.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from src.services.student_service import get_student_by_id
from src.services.prediction_service import get_prediction_history
from src.services.intervention_service import list_interventions


def generate_student_pdf_report(student_id: str, requesting_user: dict = None, conn = None) -> bytes:
    """
    Generates a formatted PDF report in bytes for a given student.
    """
    student = get_student_by_id(student_id, requesting_user=requesting_user, conn=conn)
    if not student:
        raise ValueError(f"Student '{student_id}' not found or access denied.")

    # Fetch recent predictions and interventions
    predictions = get_prediction_history(student_id=student_id, limit=3, conn=conn)
    latest_pred = predictions[0] if predictions else None

    interventions, _ = list_interventions(student_id=student_id, requesting_user=requesting_user, limit=10, conn=conn)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold',
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#64748b'),
        alignment=1
    )

    elements = []

    # 1. Header Banner
    elements.append(Paragraph("AI-BASED STUDENT PERFORMANCE ASSESSMENT REPORT", title_style))
    elements.append(Paragraph(
        f"Institution Educational Analytics Portal &bull; Generated: {datetime.now().strftime('%B %d, %Y, %I:%M %p')}<br/>"
        "Candidate Project: Asmita Chandram Kumbar | SYBSc CS (Roll No: SI1161)",
        subtitle_style
    ))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#4f46e5'), spaceAfter=15))

    # 2. Student Profile Summary Table
    elements.append(Paragraph("1. Student Behavioral & Academic Dimensions", section_style))

    att = f"{student.get('attendance_rate'):.1f}%" if student.get('attendance_rate') is not None else "N/A"
    study = f"{student.get('study_hours_per_week'):.1f} hrs/wk" if student.get('study_hours_per_week') is not None else "N/A"
    prev = f"{student.get('previous_scores'):.1f}%" if student.get('previous_scores') is not None else "N/A"
    assign = f"{student.get('assignment_completion_rate'):.1f}%" if student.get('assignment_completion_rate') is not None else "N/A"
    tutor = f"{student.get('tutoring_sessions')} sessions" if student.get('tutoring_sessions') is not None else "N/A"
    sleep = f"{student.get('sleep_hours'):.1f} hrs/night" if student.get('sleep_hours') is not None else "N/A"
    extra = "Active (Yes)" if student.get('extracurricular') == 1 else "Inactive (No)"
    net = "Available (Yes)" if student.get('internet_access') == 1 else "Unavailable (No)"

    profile_data = [
        [
            Paragraph("<b>Student ID:</b>", body_style), Paragraph(f"<b>{student.get('student_id')}</b>", body_style),
            Paragraph("<b>Attendance Rate:</b>", body_style), Paragraph(att, body_style)
        ],
        [
            Paragraph("<b>Weekly Study Hours:</b>", body_style), Paragraph(study, body_style),
            Paragraph("<b>Prior Exam Score:</b>", body_style), Paragraph(prev, body_style)
        ],
        [
            Paragraph("<b>Assignment Completion:</b>", body_style), Paragraph(assign, body_style),
            Paragraph("<b>Remedial Tutoring:</b>", body_style), Paragraph(tutor, body_style)
        ],
        [
            Paragraph("<b>Sleep Hours:</b>", body_style), Paragraph(sleep, body_style),
            Paragraph("<b>Extracurricular:</b>", body_style), Paragraph(extra, body_style)
        ],
        [
            Paragraph("<b>Internet Access:</b>", body_style), Paragraph(net, body_style),
            Paragraph("<b>Historical Exam Score:</b>", body_style),
            Paragraph(f"{student.get('final_exam_score'):.1f}%" if student.get('final_exam_score') is not None else "In Progress", body_style)
        ]
    ]

    t_profile = Table(profile_data, colWidths=[130, 130, 130, 140])
    t_profile.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t_profile)
    elements.append(Spacer(1, 15))

    # 3. Latest Predictive Assessment & Explainability
    elements.append(Paragraph("2. Supervised Machine Learning Risk Stratification", section_style))

    if latest_pred:
        risk_cat = latest_pred.get("risk_category", "Moderate Risk")
        pass_prob = latest_pred.get("pass_probability", 0.5) * 100
        fail_prob = latest_pred.get("fail_probability", 0.5) * 100

        pred_data = [
            [
                Paragraph("<b>Evaluated Model:</b>", body_style), Paragraph(latest_pred.get("model_name"), body_style),
                Paragraph("<b>Predicted Trajectory:</b>", body_style),
                Paragraph(f"<b>{latest_pred.get('outcome_label')}</b>", body_style)
            ],
            [
                Paragraph("<b>Pass Likelihood:</b>", body_style), Paragraph(f"{pass_prob:.1f}%", body_style),
                Paragraph("<b>Risk Classification:</b>", body_style),
                Paragraph(f"<b>{risk_cat}</b>", body_style)
            ]
        ]
        t_pred = Table(pred_data, colWidths=[130, 130, 130, 140])
        t_pred.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_pred)
        elements.append(Spacer(1, 10))

        # Top 3 Explainable Factors
        elements.append(Paragraph("<b>Key Contributing Factors (Model Explainability):</b>", body_style))
        top_factors = latest_pred.get("top_factors", [])
        if top_factors:
            for i, factor in enumerate(top_factors[:3], 1):
                dir_label = "[+] Positive Boost" if factor.get("direction") == "positive" else "[-] Risk Factor"
                elements.append(Paragraph(
                    f"&bull; <b>Factor {i} ({dir_label}):</b> {factor.get('description', '')}",
                    body_style
                ))
        else:
            elements.append(Paragraph("&bull; Model predictions derived from standardized multidimensional behavioral features.", body_style))
    else:
        elements.append(Paragraph("<i>No model predictions recorded for this student yet.</i>", body_style))

    elements.append(Spacer(1, 15))

    # 4. Remedial Interventions Tracker
    elements.append(Paragraph("3. Academic Remedial Action Plan & Interventions", section_style))
    if interventions:
        int_data = [
            [Paragraph("<b>Status</b>", body_style), Paragraph("<b>Title & Description</b>", body_style), Paragraph("<b>Follow-up</b>", body_style), Paragraph("<b>Advisor</b>", body_style)]
        ]
        for item in interventions:
            int_data.append([
                Paragraph(f"<b>{item.get('status')}</b>", body_style),
                Paragraph(f"<b>{item.get('title')}</b><br/>{item.get('description') or ''}", body_style),
                Paragraph(item.get("follow_up_date") or "None set", body_style),
                Paragraph(item.get("created_by") or "System", body_style)
            ])
        t_int = Table(int_data, colWidths=[80, 270, 90, 90])
        t_int.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_int)
    else:
        elements.append(Paragraph("<i>No specific remedial interventions currently open for this student.</i>", body_style))

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#cbd5e1'), spaceAfter=10))

    # 5. Ethical & Advisory Disclaimer
    elements.append(Paragraph(
        "<b>Advisory Notice:</b> Predictions support teacher judgment and are not final decisions. "
        "This system employs supervised machine learning models to forecast early academic risk trajectories "
        "and guide timely faculty interventions.",
        disclaimer_style
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
