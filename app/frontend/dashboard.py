from flask import Blueprint, render_template, session
from app.frontend.utils import api_request, login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    """Main dashboard page"""
    # Get dashboard statistics
    stats_code, stats_data = api_request("GET", "/tasks/dashboard/stats")

    # Get recent tasks
    recent_code, recent_data = api_request(
        "GET", "/tasks/dashboard/recent", params={"limit": 5}
    )

    # Get user's projects
    projects_code, projects_data = api_request("GET", "/projects")

    # Prepare data for template
    context = {
        "stats": stats_data if stats_code == 200 else {},
        "recent_tasks": recent_data if recent_code == 200 else [],
        "projects": projects_data if projects_code == 200 else [],
    }

    return render_template("dashboard/index.html", **context)
