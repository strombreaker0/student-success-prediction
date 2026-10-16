"""
WTForms definitions with CSRF tokens and server-side validation.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    FloatField, IntegerField, SelectField, TextAreaField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, NumberRange, Optional, ValidationError
)
from src.services.auth_service import validate_password_strength, validate_username


class LoginForm(FlaskForm):
    """Secure user authentication form."""
    username_or_email = StringField(
        "Username or Email",
        validators=[DataRequired(message="Please provide your username or email address."), Length(max=120)]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Please enter your password.")]
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    """
    Public student self-registration form.
    Strictly forces role to 'student' - public visitors can never create admin/faculty.
    """
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=30, message="Username must be between 3 and 30 characters.")
        ]
    )
    email = StringField(
        "Institutional Email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Please enter a valid email address."),
            Length(max=120)
        ]
    )
    full_name = StringField(
        "Full Legal Name",
        validators=[DataRequired(message="Full Name is required."), Length(min=2, max=100)]
    )
    linked_student_id = StringField(
        "Student ID (e.g. STU_1001)",
        validators=[Optional(), Length(max=30)]
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, message="Password must be at least 8 characters long.")
        ]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords must match.")
        ]
    )
    submit = SubmitField("Create Student Account")

    def validate_username(self, field):
        valid, msg = validate_username(field.data)
        if not valid:
            raise ValidationError(msg)

    def validate_password(self, field):
        valid, msg = validate_password_strength(field.data)
        if not valid:
            raise ValidationError(msg)


class ChangePasswordForm(FlaskForm):
    """User profile password update form."""
    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Please enter your current password.")]
    )
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="New password is required."),
            Length(min=8, message="Password must be at least 8 characters long.")
        ]
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Please confirm your new password."),
            EqualTo("new_password", message="Passwords must match.")
        ]
    )
    submit = SubmitField("Update Password")

    def validate_new_password(self, field):
        valid, msg = validate_password_strength(field.data)
        if not valid:
            raise ValidationError(msg)


class StudentForm(FlaskForm):
    """Form to create or edit a student record."""
    student_id = StringField(
        "Student ID",
        validators=[DataRequired(message="Student ID is required."), Length(min=2, max=30)]
    )
    attendance_rate = FloatField(
        "Attendance Rate (%)",
        validators=[
            DataRequired(message="Attendance rate is required."),
            NumberRange(min=0.0, max=100.0, message="Must be between 0% and 100%.")
        ]
    )
    study_hours_per_week = FloatField(
        "Study Hours / Week",
        validators=[
            DataRequired(message="Study hours is required."),
            NumberRange(min=0.0, max=168.0, message="Must be between 0 and 168 hours.")
        ]
    )
    previous_scores = FloatField(
        "Previous Exam Score (%)",
        validators=[
            DataRequired(message="Previous score is required."),
            NumberRange(min=0.0, max=100.0, message="Must be between 0% and 100%.")
        ]
    )
    assignment_completion_rate = FloatField(
        "Assignment Completion Rate (%)",
        validators=[
            DataRequired(message="Assignment completion is required."),
            NumberRange(min=0.0, max=100.0, message="Must be between 0% and 100%.")
        ]
    )
    tutoring_sessions = IntegerField(
        "Tutoring Sessions Attended",
        validators=[
            DataRequired(message="Tutoring sessions count is required."),
            NumberRange(min=0, max=50, message="Must be between 0 and 50.")
        ]
    )
    sleep_hours = FloatField(
        "Sleep Hours / Night",
        validators=[
            DataRequired(message="Sleep hours is required."),
            NumberRange(min=0.0, max=24.0, message="Must be between 0 and 24 hours.")
        ]
    )
    extracurricular = SelectField(
        "Extracurricular Activities",
        choices=[("1", "Participates (Yes)"), ("0", "No Participation (No)")],
        validators=[DataRequired()]
    )
    internet_access = SelectField(
        "Internet Access at Home",
        choices=[("1", "Has Access (Yes)"), ("0", "No Access (No)")],
        validators=[DataRequired()]
    )
    final_exam_score = FloatField(
        "Final Exam Score (%) [Optional Historical]",
        validators=[Optional(), NumberRange(min=0.0, max=100.0)]
    )
    passed = SelectField(
        "Final Exam Outcome [Optional Historical]",
        choices=[("", "-- None / In Progress --"), ("1", "Passed (1)"), ("0", "Failed (0)")],
        validators=[Optional()]
    )
    submit = SubmitField("Save Student Record")


class PredictionForm(FlaskForm):
    """Inference input form for real-time risk classification."""
    model_name = SelectField(
        "Machine Learning Model",
        choices=[
            ("Logistic Regression", "Logistic Regression (Primary - 80.0% Accuracy, 90.6% Recall)"),
            ("Random Forest", "Random Forest Ensemble (77.9% Accuracy)"),
            ("Decision Tree", "Decision Tree Classifier (74.2% Accuracy)")
        ],
        default="Logistic Regression",
        validators=[DataRequired()]
    )
    student_id = StringField("Student ID (Optional - to link prediction)", validators=[Optional(), Length(max=30)])
    attendance_rate = FloatField("Attendance Rate (%)", validators=[DataRequired(), NumberRange(0.0, 100.0)])
    study_hours_per_week = FloatField("Study Hours / Week", validators=[DataRequired(), NumberRange(0.0, 168.0)])
    previous_scores = FloatField("Previous Exam Score (%)", validators=[DataRequired(), NumberRange(0.0, 100.0)])
    assignment_completion_rate = FloatField("Assignment Completion Rate (%)", validators=[DataRequired(), NumberRange(0.0, 100.0)])
    tutoring_sessions = IntegerField("Tutoring Sessions Attended", validators=[DataRequired(), NumberRange(0, 50)])
    sleep_hours = FloatField("Sleep Hours / Night", validators=[DataRequired(), NumberRange(0.0, 24.0)])
    extracurricular = SelectField("Extracurricular Participation", choices=[("1", "Yes (1)"), ("0", "No (0)")], validators=[DataRequired()])
    internet_access = SelectField("Internet Access", choices=[("1", "Yes (1)"), ("0", "No (0)")], validators=[DataRequired()])
    submit = SubmitField("Generate Risk Assessment & Interventions")


class InterventionForm(FlaskForm):
    """Remedial intervention creation and update form."""
    student_id = StringField("Student ID", validators=[DataRequired(), Length(max=30)])
    title = StringField("Intervention Title", validators=[DataRequired(), Length(min=3, max=150)])
    description = TextAreaField("Action Plan & Guidance Notes", validators=[Optional(), Length(max=1000)])
    follow_up_date = StringField("Target Follow-up Date (YYYY-MM-DD)", validators=[Optional()])
    status = SelectField("Status", choices=[("Open", "Open"), ("In progress", "In progress"), ("Resolved", "Resolved")], default="Open")
    submit = SubmitField("Save Intervention")


class BatchUploadForm(FlaskForm):
    """Classroom roster CSV upload form."""
    file = FileField("CSV Student Roster", validators=[FileRequired(message="Please select a CSV file to upload.")])
    model_name = SelectField(
        "Evaluation Model",
        choices=[
            ("Logistic Regression", "Logistic Regression"),
            ("Random Forest", "Random Forest"),
            ("Decision Tree", "Decision Tree")
        ],
        default="Logistic Regression"
    )
    save_to_database = BooleanField("Persist predictions to history database")
    submit = SubmitField("Screen Cohort")
