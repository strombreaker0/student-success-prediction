"""
Security guards, RBAC decorators, URL validators, and cache-control helpers.
"""

from functools import wraps
from urllib.parse import urlparse, urljoin
from flask import request, abort, redirect, url_for, flash, make_response
from flask_login import current_user


def is_safe_url(target):
    """Validates that a redirect URL points to the same origin to prevent open-redirect exploits."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def no_cache(view_func):
    """
    Decorator that sets aggressive Cache-Control headers on the HTTP response.
    Ensures protected pages cannot be viewed via the browser's back button after logout.
    """
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        response = make_response(view_func(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response
    return decorated_view


def roles_required(*allowed_roles):
    """
    Decorator requiring the current user to possess at least one of the specified roles.
    Aborts with 403 Forbidden if unauthorized.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.path))
            if current_user.role not in allowed_roles:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator


def admin_required(view_func):
    """Decorator requiring admin role."""
    return roles_required('admin')(view_func)


def faculty_or_admin_required(view_func):
    """Decorator requiring faculty or admin role."""
    return roles_required('admin', 'faculty')(view_func)


def get_client_ip():
    """Extracts the client's IP address safely."""
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"
