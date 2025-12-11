from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.frontend.utils import api_request, login_required

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/")
@login_required
def list():
    """List all user projects"""
    status_code, projects_data = api_request("GET", "/projects")

    if status_code == 200:
        projects = projects_data or []
    else:
        projects = []
        flash("Unable to load projects.", "error")

    return render_template("projects/list.html", projects=projects)


@projects_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new project"""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")

        if not name:
            flash("Project name is required.", "error")
            return render_template("projects/form.html")

        # Call create project API
        status_code, response = api_request(
            "POST", "/projects", {"name": name, "description": description}
        )

        if status_code == 201 and response:
            flash(f'Project "{response["name"]}" created successfully!', "success")
            return redirect(url_for("projects.detail", project_id=response["id"]))
        else:
            error_msg = (
                response.get("message", "Failed to create project")
                if response
                else "Connection error"
            )
            flash(error_msg, "error")

    return render_template("projects/form.html", action="Create")


@projects_bp.route("/<int:project_id>")
@login_required
def detail(project_id):
    """View project details"""
    # Get project details
    status_code, project_data = api_request("GET", f"/projects/{project_id}")

    if status_code != 200:
        flash("Project not found.", "error")
        return redirect(url_for("projects.list"))

    # Get project members
    members_code, members_data = api_request("GET", f"/projects/{project_id}/members")

    # Get project tasks
    tasks_code, tasks_data = api_request(
        "GET", "/tasks", params={"project_id": project_id}
    )

    context = {
        "project": project_data,
        "members": members_data if members_code == 200 else [],
        "tasks": tasks_data if tasks_code == 200 else [],
    }

    return render_template("projects/detail.html", **context)


@projects_bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit(project_id):
    """Edit project details"""
    # Get current project data
    status_code, project_data = api_request("GET", f"/projects/{project_id}")

    if status_code != 200:
        flash("Project not found.", "error")
        return redirect(url_for("projects.list"))

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")

        if not name:
            flash("Project name is required.", "error")
            return render_template(
                "projects/form.html", project=project_data, action="Edit"
            )

        # Call update project API
        status_code, response = api_request(
            "PUT", f"/projects/{project_id}", {"name": name, "description": description}
        )

        if status_code == 200 and response:
            flash(f'Project "{response["name"]}" updated successfully!', "success")
            return redirect(url_for("projects.detail", project_id=project_id))
        else:
            error_msg = (
                response.get("message", "Failed to update project")
                if response
                else "Connection error"
            )
            flash(error_msg, "error")

    return render_template("projects/form.html", project=project_data, action="Edit")


@projects_bp.route("/<int:project_id>/delete", methods=["POST"])
@login_required
def delete(project_id):
    """Delete a project"""
    # Call delete project API
    status_code, response = api_request("DELETE", f"/projects/{project_id}")

    if status_code == 204:
        flash("Project deleted successfully.", "success")
    else:
        error_msg = (
            response.get("message", "Failed to delete project")
            if response
            else "Connection error"
        )
        flash(error_msg, "error")

    return redirect(url_for("projects.list"))


@projects_bp.route("/<int:project_id>/members/add", methods=["POST"])
@login_required
def add_member(project_id):
    """Add member to project"""
    user_id = request.form.get("user_id")
    role = request.form.get("role", "member")

    if not user_id:
        flash("User ID is required.", "error")
        return redirect(url_for("projects.detail", project_id=project_id))

    # Call add member API
    status_code, response = api_request(
        "POST",
        f"/projects/{project_id}/members",
        {"user_id": int(user_id), "role": role},
    )

    if status_code == 201:
        flash("Member added successfully.", "success")
    else:
        error_msg = (
            response.get("message", "Failed to add member")
            if response
            else "Connection error"
        )
        flash(error_msg, "error")

    return redirect(url_for("projects.detail", project_id=project_id))


@projects_bp.route("/<int:project_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_member(project_id, user_id):
    """Remove member from project"""
    # Call remove member API
    status_code, response = api_request(
        "DELETE", f"/projects/{project_id}/members/{user_id}"
    )

    if status_code == 204:
        flash("Member removed successfully.", "success")
    else:
        error_msg = (
            response.get("message", "Failed to remove member")
            if response
            else "Connection error"
        )
        flash(error_msg, "error")

    return redirect(url_for("projects.detail", project_id=project_id))
