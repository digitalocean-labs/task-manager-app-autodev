from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.frontend.utils import api_request, login_required

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/")
@login_required
def list():
    """List tasks with filtering"""
    # Get query parameters
    project_id = request.args.get("project_id")
    status = request.args.get("status")
    priority = request.args.get("priority")
    assigned_to = request.args.get("assigned_to")

    # Handle special filters
    if assigned_to == "me":
        assigned_to = session.get("user", {}).get("id")

    # Build API parameters
    params = {}
    if project_id:
        params["project_id"] = project_id
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if assigned_to:
        params["assigned_to"] = assigned_to

    # Get tasks
    status_code, tasks_data = api_request("GET", "/tasks", params=params)

    # Get projects for filter dropdown
    projects_code, projects_data = api_request("GET", "/projects")

    context = {
        "tasks": tasks_data if status_code == 200 else [],
        "projects": projects_data if projects_code == 200 else [],
        "filters": {
            "project_id": project_id,
            "status": status,
            "priority": priority,
            "assigned_to": request.args.get(
                "assigned_to"
            ),  # Keep original value for display
        },
    }

    return render_template("tasks/list.html", **context)


@tasks_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new task"""
    # Get projects for dropdown
    projects_code, projects_data = api_request("GET", "/projects")
    projects = projects_data if projects_code == 200 else []

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        project_id = request.form.get("project_id")
        assigned_to = request.form.get("assigned_to")
        priority = request.form.get("priority", "medium")
        due_date = request.form.get("due_date")

        if not title or not project_id:
            flash("Title and project are required.", "error")
            return render_template(
                "tasks/form.html", projects=projects, action="Create"
            )

        # Prepare task data
        task_data = {
            "title": title,
            "description": description,
            "project_id": int(project_id),
            "priority": priority,
        }

        if assigned_to:
            task_data["assigned_to"] = int(assigned_to)
        if due_date:
            task_data["due_date"] = due_date + "T23:59:59"  # Add time component

        # Call create task API
        status_code, response = api_request("POST", "/tasks", task_data)

        if status_code == 201 and response:
            flash(f'Task "{response["title"]}" created successfully!', "success")
            return redirect(url_for("tasks.detail", task_id=response["id"]))
        else:
            error_msg = (
                response.get("message", "Failed to create task")
                if response
                else "Connection error"
            )
            flash(error_msg, "error")

    return render_template("tasks/form.html", projects=projects, action="Create")


@tasks_bp.route("/<int:task_id>")
@login_required
def detail(task_id):
    """View task details"""
    # Get task details with comments
    status_code, task_data = api_request("GET", f"/tasks/{task_id}")

    if status_code != 200:
        flash("Task not found.", "error")
        return redirect(url_for("tasks.list"))

    return render_template("tasks/detail.html", task=task_data)


@tasks_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit(task_id):
    """Edit task details"""
    # Get current task data
    status_code, task_data = api_request("GET", f"/tasks/{task_id}")

    if status_code != 200:
        flash("Task not found.", "error")
        return redirect(url_for("tasks.list"))

    # Get projects for dropdown
    projects_code, projects_data = api_request("GET", "/projects")
    projects = projects_data if projects_code == 200 else []

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        assigned_to = request.form.get("assigned_to")
        priority = request.form.get("priority")
        due_date = request.form.get("due_date")

        if not title:
            flash("Title is required.", "error")
            return render_template(
                "tasks/form.html", task=task_data, projects=projects, action="Edit"
            )

        # Prepare update data
        update_data = {"title": title, "description": description, "priority": priority}

        if assigned_to:
            update_data["assigned_to"] = (
                int(assigned_to) if assigned_to != "none" else None
            )
        if due_date:
            update_data["due_date"] = due_date + "T23:59:59"

        # Call update task API
        status_code, response = api_request("PUT", f"/tasks/{task_id}", update_data)

        if status_code == 200 and response:
            flash(f'Task "{response["title"]}" updated successfully!', "success")
            return redirect(url_for("tasks.detail", task_id=task_id))
        else:
            error_msg = (
                response.get("message", "Failed to update task")
                if response
                else "Connection error"
            )
            flash(error_msg, "error")

    return render_template(
        "tasks/form.html", task=task_data, projects=projects, action="Edit"
    )


@tasks_bp.route("/<int:task_id>/status", methods=["POST"])
@login_required
def update_status(task_id):
    """Update task status"""
    new_status = request.form.get("status")

    if not new_status:
        flash("Status is required.", "error")
        return redirect(url_for("tasks.detail", task_id=task_id))

    # Call update status API
    status_code, response = api_request(
        "PATCH", f"/tasks/{task_id}/status", {"status": new_status}
    )

    if status_code == 200:
        flash(
            f'Task status updated to {new_status.replace("_", " ").title()}.', "success"
        )
    else:
        error_msg = (
            response.get("message", "Failed to update status")
            if response
            else "Connection error"
        )
        flash(error_msg, "error")

    return redirect(url_for("tasks.detail", task_id=task_id))


@tasks_bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete(task_id):
    """Delete a task"""
    # Call delete task API
    status_code, response = api_request("DELETE", f"/tasks/{task_id}")

    if status_code == 204:
        flash("Task deleted successfully.", "success")
    else:
        error_msg = (
            response.get("message", "Failed to delete task")
            if response
            else "Connection error"
        )
        flash(error_msg, "error")

    return redirect(url_for("tasks.list"))


@tasks_bp.route("/<int:task_id>/comments", methods=["POST"])
@login_required
def add_comment(task_id):
    """Add comment to task"""
    comment_text = request.form.get("comment_text")

    if not comment_text:
        flash("Comment text is required.", "error")
        return redirect(url_for("tasks.detail", task_id=task_id))

    # Call add comment API
    status_code, response = api_request(
        "POST", "/comments", {"task_id": task_id, "comment_text": comment_text}
    )

    if status_code == 201:
        flash("Comment added successfully.", "success")
    else:
        error_msg = (
            response.get("message", "Failed to add comment")
            if response
            else "Connection error"
        )
        flash(error_msg, "error")

    return redirect(url_for("tasks.detail", task_id=task_id))
