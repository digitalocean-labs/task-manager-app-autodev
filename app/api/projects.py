from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields as ma_fields, validate, ValidationError
from app import db
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember

projects_ns = Namespace("projects", description="Project management operations")


# Marshmallow schemas for input validation
class ProjectCreateSchema(Schema):
    name = ma_fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = ma_fields.Str(allow_none=True, validate=validate.Length(max=1000))


class ProjectUpdateSchema(Schema):
    name = ma_fields.Str(validate=validate.Length(min=1, max=200))
    description = ma_fields.Str(allow_none=True, validate=validate.Length(max=1000))


class ProjectMemberAddSchema(Schema):
    user_id = ma_fields.Int(required=True)
    role = ma_fields.Str(validate=validate.OneOf(["admin", "member", "viewer"]))


# Flask-RESTX models for Swagger documentation
project_create_model = projects_ns.model(
    "ProjectCreate",
    {
        "name": fields.String(
            required=True, description="Project name", example="My Project"
        ),
        "description": fields.String(
            description="Project description",
            example="A sample project for task management",
        ),
    },
)

project_update_model = projects_ns.model(
    "ProjectUpdate",
    {
        "name": fields.String(description="Project name"),
        "description": fields.String(description="Project description"),
    },
)

project_model = projects_ns.model(
    "Project",
    {
        "id": fields.Integer(description="Project ID"),
        "name": fields.String(description="Project name"),
        "description": fields.String(description="Project description"),
        "owner_id": fields.Integer(description="Project owner ID"),
        "created_at": fields.String(description="Creation date"),
        "updated_at": fields.String(description="Last update date"),
        "is_active": fields.Boolean(description="Project status"),
    },
)

project_with_stats_model = projects_ns.model(
    "ProjectWithStats",
    {
        "id": fields.Integer(description="Project ID"),
        "name": fields.String(description="Project name"),
        "description": fields.String(description="Project description"),
        "owner_id": fields.Integer(description="Project owner ID"),
        "created_at": fields.String(description="Creation date"),
        "updated_at": fields.String(description="Last update date"),
        "is_active": fields.Boolean(description="Project status"),
        "stats": fields.Raw(description="Project statistics"),
    },
)

member_add_model = projects_ns.model(
    "MemberAdd",
    {
        "user_id": fields.Integer(required=True, description="User ID to add"),
        "role": fields.String(
            description="Member role (admin/member/viewer)", default="member"
        ),
    },
)

member_model = projects_ns.model(
    "ProjectMember",
    {
        "user_id": fields.Integer(description="User ID"),
        "role": fields.String(description="Member role"),
        "joined_at": fields.String(description="Join date"),
        "user_name": fields.String(description="User full name"),
        "user_email": fields.String(description="User email"),
    },
)


@projects_ns.route("")
class ProjectList(Resource):
    @jwt_required()
    @projects_ns.marshal_list_with(project_with_stats_model)
    @projects_ns.response(401, "Authentication required")
    def get(self):
        """Get list of user's projects"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            projects_ns.abort(404, "User not found")

        projects = user.get_projects()
        return [project.to_dict(include_stats=True) for project in projects]

    @jwt_required()
    @projects_ns.expect(project_create_model)
    @projects_ns.marshal_with(project_model, code=201)
    @projects_ns.response(400, "Validation error")
    @projects_ns.response(401, "Authentication required")
    def post(self):
        """Create a new project"""
        user_id = get_jwt_identity()

        try:
            # Validate input data
            schema = ProjectCreateSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            projects_ns.abort(400, f"Validation error: {err.messages}")

        # Create new project
        project = Project(
            name=data["name"], description=data.get("description"), owner_id=user_id
        )

        db.session.add(project)
        db.session.commit()

        return project.to_dict(), 201


@projects_ns.route("/<int:project_id>")
class ProjectDetail(Resource):
    @jwt_required()
    @projects_ns.marshal_with(project_with_stats_model)
    @projects_ns.response(401, "Authentication required")
    @projects_ns.response(403, "Access denied")
    @projects_ns.response(404, "Project not found")
    def get(self, project_id):
        """Get project details"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            projects_ns.abort(404, "User not found")

        if not user.can_access_project(project_id):
            projects_ns.abort(403, "Access denied")

        project = Project.query.get(project_id)
        if not project:
            projects_ns.abort(404, "Project not found")

        return project.to_dict(include_stats=True)

    @jwt_required()
    @projects_ns.expect(project_update_model)
    @projects_ns.marshal_with(project_model)
    @projects_ns.response(400, "Validation error")
    @projects_ns.response(401, "Authentication required")
    @projects_ns.response(403, "Access denied")
    @projects_ns.response(404, "Project not found")
    def put(self, project_id):
        """Update project details"""
        user_id = get_jwt_identity()

        project = Project.query.get(project_id)
        if not project:
            projects_ns.abort(404, "Project not found")

        # Check if user can edit project (owner or admin)
        if project.owner_id != user_id:
            member = ProjectMember.query.filter_by(
                project_id=project_id, user_id=user_id
            ).first()
            if not member or member.role not in ["admin"]:
                projects_ns.abort(403, "Access denied")

        try:
            # Validate input data
            schema = ProjectUpdateSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            projects_ns.abort(400, f"Validation error: {err.messages}")

        # Update project fields
        if "name" in data:
            project.name = data["name"]
        if "description" in data:
            project.description = data["description"]

        db.session.commit()

        return project.to_dict()

    @jwt_required()
    @projects_ns.response(204, "Project deleted")
    @projects_ns.response(401, "Authentication required")
    @projects_ns.response(403, "Access denied")
    @projects_ns.response(404, "Project not found")
    def delete(self, project_id):
        """Delete project (soft delete)"""
        user_id = get_jwt_identity()

        project = Project.query.get(project_id)
        if not project:
            projects_ns.abort(404, "Project not found")

        # Only project owner can delete
        if project.owner_id != user_id:
            projects_ns.abort(403, "Only project owner can delete project")

        # Soft delete
        project.is_active = False
        db.session.commit()

        return "", 204


@projects_ns.route("/<int:project_id>/members")
class ProjectMembers(Resource):
    @jwt_required()
    @projects_ns.marshal_list_with(member_model)
    @projects_ns.response(401, "Authentication required")
    @projects_ns.response(403, "Access denied")
    @projects_ns.response(404, "Project not found")
    def get(self, project_id):
        """Get project members"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            projects_ns.abort(404, "User not found")

        if not user.can_access_project(project_id):
            projects_ns.abort(403, "Access denied")

        project = Project.query.get(project_id)
        if not project:
            projects_ns.abort(404, "Project not found")

        members = []
        # Add owner
        owner = User.query.get(project.owner_id)
        if owner:
            members.append(
                {
                    "user_id": owner.id,
                    "role": "owner",
                    "joined_at": project.created_at.isoformat(),
                    "user_name": owner.full_name,
                    "user_email": owner.email,
                }
            )

        # Add project members
        project_members = ProjectMember.query.filter_by(project_id=project_id).all()
        for member in project_members:
            if member.user:
                members.append(member.to_dict())

        return members

    @jwt_required()
    @projects_ns.expect(member_add_model)
    @projects_ns.marshal_with(member_model, code=201)
    @projects_ns.response(400, "Validation error")
    @projects_ns.response(401, "Authentication required")
    @projects_ns.response(403, "Access denied")
    @projects_ns.response(404, "Project or user not found")
    @projects_ns.response(409, "User already a member")
    def post(self, project_id):
        """Add member to project"""
        user_id = get_jwt_identity()

        project = Project.query.get(project_id)
        if not project:
            projects_ns.abort(404, "Project not found")

        # Check if user can manage members (owner or admin)
        if project.owner_id != user_id:
            member = ProjectMember.query.filter_by(
                project_id=project_id, user_id=user_id
            ).first()
            if not member or member.role not in ["admin"]:
                projects_ns.abort(403, "Access denied")

        try:
            # Validate input data
            schema = ProjectMemberAddSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            projects_ns.abort(400, f"Validation error: {err.messages}")

        # Check if user exists
        target_user = User.query.get(data["user_id"])
        if not target_user:
            projects_ns.abort(404, "User not found")

        # Add member to project
        success = project.add_member(data["user_id"], data.get("role", "member"))

        if not success:
            projects_ns.abort(409, "User already a member or is project owner")

        db.session.commit()

        # Return the new member info
        new_member = ProjectMember.query.filter_by(
            project_id=project_id, user_id=data["user_id"]
        ).first()

        return new_member.to_dict(), 201


@projects_ns.route("/<int:project_id>/members/<int:user_id>")
class ProjectMemberDetail(Resource):
    @jwt_required()
    @projects_ns.response(204, "Member removed")
    @projects_ns.response(401, "Authentication required")
    @projects_ns.response(403, "Access denied")
    @projects_ns.response(404, "Project or member not found")
    def delete(self, project_id, user_id):
        """Remove member from project"""
        current_user_id = get_jwt_identity()

        project = Project.query.get(project_id)
        if not project:
            projects_ns.abort(404, "Project not found")

        # Check if user can manage members (owner or admin)
        if project.owner_id != current_user_id:
            member = ProjectMember.query.filter_by(
                project_id=project_id, user_id=current_user_id
            ).first()
            if not member or member.role not in ["admin"]:
                projects_ns.abort(403, "Access denied")

        # Remove member from project
        success = project.remove_member(user_id)

        if not success:
            projects_ns.abort(404, "Member not found or cannot remove project owner")

        db.session.commit()

        return "", 204


@projects_ns.route("/<int:project_id>/analytics")
class ProjectAnalytics(Resource):
    @jwt_required()
    @projects_ns.marshal_with(fields.Raw)
    @projects_ns.response(401, "Authentication required")
    @projects_ns.response(403, "Access denied")
    @projects_ns.response(404, "Project not found")
    def get(self, project_id):
        """Get project analytics and statistics"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            projects_ns.abort(404, "User not found")

        if not user.can_access_project(project_id):
            projects_ns.abort(403, "Access denied")

        project = Project.query.get(project_id)
        if not project:
            projects_ns.abort(404, "Project not found")

        # Get detailed analytics
        stats = project.get_task_stats()
        members = project.get_members()

        analytics = {
            "project_id": project_id,
            "project_name": project.name,
            "task_statistics": stats,
            "member_count": len(members),
            "project_age_days": (project.updated_at - project.created_at).days,
            "last_activity": project.updated_at.isoformat(),
        }

        return analytics
