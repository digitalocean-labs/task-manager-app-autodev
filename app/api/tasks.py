from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields as ma_fields, validate, ValidationError
from datetime import datetime
from app import db
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.project_member import ProjectMember

tasks_ns = Namespace("tasks", description="Task management operations")


# Marshmallow schemas for input validation
class TaskCreateSchema(Schema):
    title = ma_fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = ma_fields.Str(allow_none=True, validate=validate.Length(max=2000))
    project_id = ma_fields.Int(required=True)
    assigned_to = ma_fields.Int(allow_none=True)
    priority = ma_fields.Str(
        validate=validate.OneOf(["low", "medium", "high", "critical"])
    )
    due_date = ma_fields.DateTime(allow_none=True)


class TaskUpdateSchema(Schema):
    title = ma_fields.Str(validate=validate.Length(min=1, max=200))
    description = ma_fields.Str(allow_none=True, validate=validate.Length(max=2000))
    assigned_to = ma_fields.Int(allow_none=True)
    priority = ma_fields.Str(
        validate=validate.OneOf(["low", "medium", "high", "critical"])
    )
    due_date = ma_fields.DateTime(allow_none=True)


class TaskStatusUpdateSchema(Schema):
    status = ma_fields.Str(
        required=True,
        validate=validate.OneOf(["pending", "in_progress", "completed", "cancelled"]),
    )


# Flask-RESTX models for Swagger documentation
task_create_model = tasks_ns.model(
    "TaskCreate",
    {
        "title": fields.String(
            required=True,
            description="Task title",
            example="Implement user authentication",
        ),
        "description": fields.String(
            description="Task description",
            example="Create login and registration functionality",
        ),
        "project_id": fields.Integer(
            required=True, description="Project ID", example=1
        ),
        "assigned_to": fields.Integer(description="Assigned user ID", example=2),
        "priority": fields.String(
            description="Task priority",
            enum=["low", "medium", "high", "critical"],
            default="medium",
        ),
        "due_date": fields.DateTime(
            description="Due date (ISO format)", example="2024-12-31T23:59:59"
        ),
    },
)

task_update_model = tasks_ns.model(
    "TaskUpdate",
    {
        "title": fields.String(description="Task title"),
        "description": fields.String(description="Task description"),
        "assigned_to": fields.Integer(description="Assigned user ID"),
        "priority": fields.String(
            description="Task priority", enum=["low", "medium", "high", "critical"]
        ),
        "due_date": fields.DateTime(description="Due date (ISO format)"),
    },
)

task_status_model = tasks_ns.model(
    "TaskStatus",
    {
        "status": fields.String(
            required=True,
            description="Task status",
            enum=["pending", "in_progress", "completed", "cancelled"],
        )
    },
)

task_model = tasks_ns.model(
    "Task",
    {
        "id": fields.Integer(description="Task ID"),
        "title": fields.String(description="Task title"),
        "description": fields.String(description="Task description"),
        "status": fields.String(description="Task status"),
        "priority": fields.String(description="Task priority"),
        "project_id": fields.Integer(description="Project ID"),
        "assigned_to": fields.Integer(description="Assigned user ID"),
        "created_by": fields.Integer(description="Creator user ID"),
        "due_date": fields.String(description="Due date"),
        "created_at": fields.String(description="Creation date"),
        "updated_at": fields.String(description="Last update date"),
        "is_overdue": fields.Boolean(description="Overdue status"),
        "comments_count": fields.Integer(description="Number of comments"),
    },
)

task_with_comments_model = tasks_ns.model(
    "TaskWithComments",
    {
        "id": fields.Integer(description="Task ID"),
        "title": fields.String(description="Task title"),
        "description": fields.String(description="Task description"),
        "status": fields.String(description="Task status"),
        "priority": fields.String(description="Task priority"),
        "project_id": fields.Integer(description="Project ID"),
        "assigned_to": fields.Integer(description="Assigned user ID"),
        "created_by": fields.Integer(description="Creator user ID"),
        "due_date": fields.String(description="Due date"),
        "created_at": fields.String(description="Creation date"),
        "updated_at": fields.String(description="Last update date"),
        "is_overdue": fields.Boolean(description="Overdue status"),
        "comments_count": fields.Integer(description="Number of comments"),
        "comments": fields.List(fields.Raw, description="Task comments"),
    },
)


@tasks_ns.route("")
class TaskList(Resource):
    @jwt_required()
    @tasks_ns.marshal_list_with(task_model)
    @tasks_ns.param("project_id", "Filter by project ID")
    @tasks_ns.param("status", "Filter by status")
    @tasks_ns.param("priority", "Filter by priority")
    @tasks_ns.param("assigned_to", "Filter by assigned user")
    @tasks_ns.param("limit", "Limit number of results")
    @tasks_ns.param("offset", "Offset for pagination")
    @tasks_ns.response(401, "Authentication required")
    def get(self):
        """Get list of tasks with optional filtering"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            tasks_ns.abort(404, "User not found")

        # Get query parameters
        project_id = request.args.get("project_id", type=int)
        status = request.args.get("status")
        priority = request.args.get("priority")
        assigned_to = request.args.get("assigned_to", type=int)
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        # If project_id is specified, check access
        if project_id:
            if not user.can_access_project(project_id):
                tasks_ns.abort(403, "Access denied to project")

        # Get tasks with filters
        tasks = Task.get_tasks_by_filters(
            project_id=project_id,
            assigned_to=assigned_to,
            status=status,
            priority=priority,
            limit=limit,
            offset=offset,
        )

        # Filter tasks user can view
        accessible_tasks = []
        for task in tasks:
            if task.can_user_view(user_id):
                accessible_tasks.append(task)

        return [task.to_dict() for task in accessible_tasks]

    @jwt_required()
    @tasks_ns.expect(task_create_model)
    @tasks_ns.marshal_with(task_model, code=201)
    @tasks_ns.response(400, "Validation error")
    @tasks_ns.response(401, "Authentication required")
    @tasks_ns.response(403, "Access denied")
    @tasks_ns.response(404, "Project not found")
    def post(self):
        """Create a new task"""
        user_id = get_jwt_identity()

        try:
            # Validate input data
            schema = TaskCreateSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            tasks_ns.abort(400, f"Validation error: {err.messages}")

        # Check if user has access to the project
        user = User.query.get(user_id)
        if not user or not user.can_access_project(data["project_id"]):
            tasks_ns.abort(403, "Access denied to project")

        # Check if project exists
        project = Project.query.get(data["project_id"])
        if not project:
            tasks_ns.abort(404, "Project not found")

        # If assigned_to is specified, check if that user has access to project
        if data.get("assigned_to"):
            assigned_user = User.query.get(data["assigned_to"])
            if not assigned_user or not assigned_user.can_access_project(
                data["project_id"]
            ):
                tasks_ns.abort(400, "Assigned user does not have access to project")

        # Create new task
        task = Task(
            title=data["title"],
            description=data.get("description"),
            project_id=data["project_id"],
            created_by=user_id,
            assigned_to=data.get("assigned_to"),
            priority=data.get("priority", "medium"),
            due_date=data.get("due_date"),
        )

        db.session.add(task)
        db.session.commit()

        return task.to_dict(), 201


@tasks_ns.route("/<int:task_id>")
class TaskDetail(Resource):
    @jwt_required()
    @tasks_ns.marshal_with(task_with_comments_model)
    @tasks_ns.response(401, "Authentication required")
    @tasks_ns.response(403, "Access denied")
    @tasks_ns.response(404, "Task not found")
    def get(self, task_id):
        """Get task details with comments"""
        user_id = get_jwt_identity()

        task = Task.query.get(task_id)
        if not task:
            tasks_ns.abort(404, "Task not found")

        if not task.can_user_view(user_id):
            tasks_ns.abort(403, "Access denied")

        return task.to_dict(include_comments=True)

    @jwt_required()
    @tasks_ns.expect(task_update_model)
    @tasks_ns.marshal_with(task_model)
    @tasks_ns.response(400, "Validation error")
    @tasks_ns.response(401, "Authentication required")
    @tasks_ns.response(403, "Access denied")
    @tasks_ns.response(404, "Task not found")
    def put(self, task_id):
        """Update task details"""
        user_id = get_jwt_identity()

        task = Task.query.get(task_id)
        if not task:
            tasks_ns.abort(404, "Task not found")

        if not task.can_user_edit(user_id):
            tasks_ns.abort(403, "Access denied")

        try:
            # Validate input data
            schema = TaskUpdateSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            tasks_ns.abort(400, f"Validation error: {err.messages}")

        # Update task fields
        if "title" in data:
            task.title = data["title"]
        if "description" in data:
            task.description = data["description"]
        if "priority" in data:
            task.priority = data["priority"]
        if "due_date" in data:
            task.due_date = data["due_date"]

        # Handle assignment change
        if "assigned_to" in data:
            if data["assigned_to"]:
                # Check if assigned user has access to project
                assigned_user = User.query.get(data["assigned_to"])
                if not assigned_user or not assigned_user.can_access_project(
                    task.project_id
                ):
                    tasks_ns.abort(400, "Assigned user does not have access to project")
                task.assign_to_user(data["assigned_to"])
            else:
                task.unassign()

        db.session.commit()

        return task.to_dict()

    @jwt_required()
    @tasks_ns.response(204, "Task deleted")
    @tasks_ns.response(401, "Authentication required")
    @tasks_ns.response(403, "Access denied")
    @tasks_ns.response(404, "Task not found")
    def delete(self, task_id):
        """Delete task"""
        user_id = get_jwt_identity()

        task = Task.query.get(task_id)
        if not task:
            tasks_ns.abort(404, "Task not found")

        if not task.can_user_edit(user_id):
            tasks_ns.abort(403, "Access denied")

        db.session.delete(task)
        db.session.commit()

        return "", 204


@tasks_ns.route("/<int:task_id>/status")
class TaskStatus(Resource):
    @jwt_required()
    @tasks_ns.expect(task_status_model)
    @tasks_ns.marshal_with(task_model)
    @tasks_ns.response(400, "Validation error")
    @tasks_ns.response(401, "Authentication required")
    @tasks_ns.response(403, "Access denied")
    @tasks_ns.response(404, "Task not found")
    def patch(self, task_id):
        """Update task status"""
        user_id = get_jwt_identity()

        task = Task.query.get(task_id)
        if not task:
            tasks_ns.abort(404, "Task not found")

        if not task.can_user_edit(user_id):
            tasks_ns.abort(403, "Access denied")

        try:
            # Validate input data
            schema = TaskStatusUpdateSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            tasks_ns.abort(400, f"Validation error: {err.messages}")

        # Update task status
        success = task.update_status(data["status"])
        if not success:
            tasks_ns.abort(400, "Invalid status")

        db.session.commit()

        return task.to_dict()


@tasks_ns.route("/dashboard/stats")
class DashboardStats(Resource):
    @jwt_required()
    @tasks_ns.marshal_with(fields.Raw)
    @tasks_ns.response(401, "Authentication required")
    def get(self):
        """Get user dashboard statistics"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            tasks_ns.abort(404, "User not found")

        # Get user's accessible projects
        projects = user.get_projects()
        project_ids = [p.id for p in projects]

        # Get task statistics
        total_tasks = Task.query.filter(Task.project_id.in_(project_ids)).count()
        assigned_tasks = Task.query.filter(
            Task.project_id.in_(project_ids), Task.assigned_to == user_id
        ).count()
        created_tasks = Task.query.filter(
            Task.project_id.in_(project_ids), Task.created_by == user_id
        ).count()

        completed_tasks = Task.query.filter(
            Task.project_id.in_(project_ids),
            Task.assigned_to == user_id,
            Task.status == "completed",
        ).count()

        overdue_tasks = Task.query.filter(
            Task.project_id.in_(project_ids),
            Task.assigned_to == user_id,
            Task.due_date < datetime.utcnow(),
            Task.status.notin_(["completed", "cancelled"]),
        ).count()

        stats = {
            "total_projects": len(projects),
            "total_tasks": total_tasks,
            "assigned_tasks": assigned_tasks,
            "created_tasks": created_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "completion_rate": (completed_tasks / assigned_tasks * 100)
            if assigned_tasks > 0
            else 0,
        }

        return stats


@tasks_ns.route("/dashboard/recent")
class RecentTasks(Resource):
    @jwt_required()
    @tasks_ns.marshal_list_with(task_model)
    @tasks_ns.param("limit", "Limit number of results", default=10)
    @tasks_ns.response(401, "Authentication required")
    def get(self):
        """Get recent tasks for dashboard"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            tasks_ns.abort(404, "User not found")

        limit = request.args.get("limit", 10, type=int)

        # Get user's accessible projects
        projects = user.get_projects()
        project_ids = [p.id for p in projects]

        # Get recent tasks (assigned to user or created by user)
        recent_tasks = (
            Task.query.filter(
                Task.project_id.in_(project_ids),
                db.or_(Task.assigned_to == user_id, Task.created_by == user_id),
            )
            .order_by(Task.updated_at.desc())
            .limit(limit)
            .all()
        )

        return [task.to_dict() for task in recent_tasks]
