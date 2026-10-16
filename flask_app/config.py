"""
Flask Application Configuration.
Defines base, development, production, and testing configurations with secure cookie handling,
session timeouts, and configurable database locations.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "database", "student_success.db")


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "academic-predict-dev-secret-key-change-in-production-2026")
    STUDENT_DB_PATH = os.environ.get("STUDENT_DB_PATH", DEFAULT_DB_PATH)

    # Session and Cookie Security
    SESSION_COOKIE_NAME = "edu_analytics_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SECURE_COOKIES", "0").lower() in ("1", "true", "yes")
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get("SESSION_TIMEOUT_MINUTES", 60)))

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Valid for session lifetime

    # Demonstration Mode & One-Click Demo Access
    ENABLE_DEMO_LOGIN = os.environ.get("ENABLE_DEMO_LOGIN", "1").lower() in ("1", "true", "yes")

    # Application details
    APP_NAME = "AI-Based Student Academic Success Prediction System"
    CANDIDATE_NAME = "Asmita Chandram Kumbar"
    CANDIDATE_CLASS = "SYBSc CS (2nd Year)"
    CANDIDATE_ROLL = "SI1161"


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production environment configuration with strict HTTPS enforcement."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration with disabled CSRF and isolated database."""
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
