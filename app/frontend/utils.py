import requests
from flask import session, current_app, redirect, url_for, flash
from functools import wraps


def api_request(method, endpoint, data=None, params=None):
    """Make authenticated API requests"""
    base_url = current_app.config.get("API_BASE_URL", "http://localhost:5000")
    url = f"{base_url}/api{endpoint}"

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # Add JWT token if available
    token = session.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return None, None

        # Handle different response codes
        if response.status_code == 401:
            # Token expired, clear session
            session.clear()
            return None, {"error": "Authentication required"}

        # Try to parse JSON response
        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, {"message": response.text}

    except requests.RequestException as e:
        return None, {"error": f"Connection error: {str(e)}"}


def login_required(f):
    """Decorator to require login for routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("access_token"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def format_datetime(dt_string):
    """Format datetime string for display"""
    if not dt_string:
        return ""

    try:
        from datetime import datetime

        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return dt_string


def get_priority_class(priority):
    """Get CSS class for priority level"""
    priority_classes = {
        "low": "badge-secondary",
        "medium": "badge-primary",
        "high": "badge-warning",
        "critical": "badge-danger",
    }
    return priority_classes.get(priority, "badge-secondary")


def get_status_class(status):
    """Get CSS class for task status"""
    status_classes = {
        "pending": "badge-light",
        "in_progress": "badge-info",
        "completed": "badge-success",
        "cancelled": "badge-dark",
    }
    return status_classes.get(status, "badge-light")
