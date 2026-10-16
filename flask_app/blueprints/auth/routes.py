"""
Authentication Blueprint Routes:
Handles login, registration, logout, and profile/password management.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from src.services.auth_service import (
    authenticate_user, register_user, verify_password, hash_password,
    is_rate_limited
)
from src.services.audit_service import log_audit_event
from src.db.connection import get_db_connection
from flask_app.forms import LoginForm, RegistrationForm, ChangePasswordForm
from flask_app.models import User
from flask_app.security import is_safe_url, no_cache, get_client_ip

auth_bp = Blueprint('auth', __name__, template_folder='../../templates/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.username_or_email.data.strip()
        pwd = form.password.data

        if is_rate_limited(identifier):
            flash("Too many failed login attempts. Please wait 15 minutes before trying again.", "danger")
            log_audit_event(identifier, "LOGIN_RATE_LIMITED", target="auth", ip_address=get_client_ip())
            return render_template('auth/login.html', form=form)

        auth_ok, auth_msg, user_dict = authenticate_user(identifier, pwd)
        if auth_ok and user_dict:
            user = User.get_by_id(user_dict["id"])
            if user and user.is_active:
                # Regenerate session to protect against session fixation
                session.clear()
                login_user(user, remember=form.remember_me.data)
                log_audit_event(user.username, "LOGIN_SUCCESS", target="auth", user_id=user.id, ip_address=get_client_ip())
                flash(f"Welcome back, {user.full_name}!", "success")

                next_page = request.args.get('next')
                if next_page and is_safe_url(next_page):
                    return redirect(next_page)
                return redirect(url_for('main.dashboard'))

        # Generic failure message to prevent username enumeration
        log_audit_event(identifier, "LOGIN_FAILURE", target="auth", ip_address=get_client_ip())
        flash("Invalid username/email or password.", "danger")

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        ok, msg, created_user = register_user(
            username=form.username.data.strip(),
            email=form.email.data.strip(),
            password=form.password.data,
            role="student",  # Public registration strictly forces role=student
            full_name=form.full_name.data.strip(),
            linked_student_id=form.linked_student_id.data.strip() if form.linked_student_id.data else None
        )
        if ok:
            log_audit_event(
                form.username.data.strip(),
                "REGISTER_SUCCESS",
                target=f"role=student, id={form.linked_student_id.data}",
                ip_address=get_client_ip()
            )
            flash("Your student account has been created successfully! Please sign in.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash(msg, "danger")

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    username = current_user.username
    uid = current_user.id
    logout_user()
    session.clear()
    log_audit_event(username, "LOGOUT", target="auth", user_id=uid, ip_address=get_client_ip())
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@no_cache
def profile():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE id = ?;", (current_user.id,))
            row = cursor.fetchone()
            if not row or not verify_password(row["password_hash"], form.current_password.data):
                flash("Current password is incorrect.", "danger")
            else:
                new_hash = hash_password(form.new_password.data)
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (new_hash, current_user.id))
                conn.commit()
                log_audit_event(
                    current_user.username,
                    "PASSWORD_CHANGE",
                    target=f"user_id={current_user.id}",
                    user_id=current_user.id,
                    ip_address=get_client_ip()
                )
                flash("Password updated successfully.", "success")
                return redirect(url_for('auth.profile'))
        finally:
            conn.close()

    return render_template('auth/profile.html', user=current_user, form=form)
