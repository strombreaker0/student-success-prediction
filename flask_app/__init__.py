"""
Flask Application Factory.
Initializes extensions (Flask-Login, Flask-WTF CSRF), registers Blueprints,
configures security headers, custom error pages, and administrative CLI commands.
"""

import os
import click
from datetime import datetime
from flask import Flask, render_template, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from flask_app.config import DevelopmentConfig, Config
from flask_app.models import User, AnonymousUser
from src.db.connection import get_db_connection
from src.db.init_app_db import ensure_db_initialized

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_class=DevelopmentConfig):
    """Factory function to build and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Initialize extensions
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.anonymous_user = AnonymousUser

    # Configure Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access the Educational Analytics Portal."
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    # Ensure database schema, enhancements, and baseline data are ready
    with app.app_context():
        try:
            conn = get_db_connection(app.config.get("STUDENT_DB_PATH"))
            seed_csv = not app.config.get("TESTING", False)
            ensure_db_initialized(conn=conn, seed_csv_if_empty=seed_csv)
            conn.close()
        except Exception as e:
            app.logger.error(f"Database initialization error on startup: {e}")
            if not app.config.get("TESTING", False):
                raise

    # Register Blueprints
    from flask_app.blueprints.auth.routes import auth_bp
    from flask_app.blueprints.main.routes import main_bp
    from flask_app.blueprints.students.routes import students_bp
    from flask_app.blueprints.predictions.routes import predictions_bp
    from flask_app.blueprints.transparency.routes import transparency_bp
    from flask_app.blueprints.interventions.routes import interventions_bp
    from flask_app.blueprints.audit.routes import audit_bp
    from flask_app.blueprints.api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(transparency_bp)
    app.register_blueprint(interventions_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(api_bp)

    # Global Response Security Headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # Global Template Context
    @app.context_processor
    def inject_global_template_vars():
        return {
            "current_year": datetime.now().year,
            "candidate_name": app.config.get("CANDIDATE_NAME", "Asmita Chandram Kumbar"),
            "candidate_class": app.config.get("CANDIDATE_CLASS", "SYBSc CS (2nd Year)"),
            "candidate_roll": app.config.get("CANDIDATE_ROLL", "SI1161"),
            "app_name": app.config.get("APP_NAME", "AI-Based Student Academic Success Prediction System")
        }

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    # CLI Commands
    @app.cli.command("seed-demo")
    @click.option("--reset/--no-reset", default=False, help="Whether to seed fresh sample data")
    def seed_demo_command(reset):
        """Opt-in, idempotent demo-data seeding command (Priority 3)."""
        from src.services.student_service import add_student
        click.echo("Seeding opt-in demo student records...")
        sample_students = [
            {"student_id": "STU_DEMO01", "attendance_rate": 92.5, "study_hours_per_week": 18.0, "previous_scores": 82.0, "assignment_completion_rate": 95.0, "tutoring_sessions": 3, "sleep_hours": 7.5, "extracurricular": 1, "internet_access": 1, "passed": 1, "final_exam_score": 85.0},
            {"student_id": "STU_DEMO02", "attendance_rate": 54.0, "study_hours_per_week": 6.5, "previous_scores": 45.0, "assignment_completion_rate": 58.0, "tutoring_sessions": 0, "sleep_hours": 5.0, "extracurricular": 0, "internet_access": 1, "passed": 0, "final_exam_score": 38.0},
            {"student_id": "STU_DEMO03", "attendance_rate": 78.0, "study_hours_per_week": 13.5, "previous_scores": 68.0, "assignment_completion_rate": 76.0, "tutoring_sessions": 2, "sleep_hours": 7.0, "extracurricular": 1, "internet_access": 1, "passed": 1, "final_exam_score": 67.0}
        ]
        conn = get_db_connection(app.config.get("STUDENT_DB_PATH"))
        try:
            for s in sample_students:
                add_student(s, conn=conn)
            click.echo("Demo student data seeded idempotently.")
        finally:
            conn.close()

    @app.cli.command("create-admin")
    @click.option("--username", prompt="Admin username", help="Admin username")
    @click.option("--email", prompt="Admin email", help="Admin email")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
    @click.option("--name", prompt="Full name", default="Administrator", help="Admin full name")
    def create_admin_command(username, email, password, name):
        """Securely provision an administrator via CLI."""
        from src.services.auth_service import register_user
        conn = get_db_connection(app.config.get("STUDENT_DB_PATH"))
        try:
            ok, msg, u = register_user(
                username=username,
                email=email,
                password=password,
                role="admin",
                full_name=name,
                conn=conn
            )
            if ok:
                click.echo(f"Administrator '{username}' created successfully.")
            else:
                click.echo(f"Error creating admin: {msg}")
        finally:
            conn.close()

    @app.cli.command("create-demo-accounts")
    @click.option("--admin-password", default=None, help="Custom password for demo admin account")
    @click.option("--student-password", default=None, help="Custom password for demo student account")
    def create_demo_accounts_command(admin_password, student_password):
        """Idempotently provisions secure demo accounts (Admin & Student) with synthetic profile."""
        from src.services.demo_service import provision_demo_accounts
        conn = get_db_connection(app.config.get("STUDENT_DB_PATH"))
        try:
            res = provision_demo_accounts(
                admin_password=admin_password,
                student_password=student_password,
                conn=conn
            )
            click.echo("Demo accounts provisioned successfully:")
            click.echo(f"  - Admin:   username='{res['admin']['username']}', role='{res['admin']['role']}' ({res['admin']['action']})")
            click.echo(f"  - Student: username='{res['student']['username']}', role='{res['student']['role']}', linked_id='{res['student']['linked_student_id']}' ({res['student']['action']})")
        finally:
            conn.close()

    return app
