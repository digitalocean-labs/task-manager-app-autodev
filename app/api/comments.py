from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields as ma_fields, validate, ValidationError
from app import db
from app.models.user import User
from app.models.task import Task
from app.models.comment import TaskComment

comments_ns = Namespace("comments", description="Comment management operations")


# Marshmallow schemas for input validation
class CommentCreateSchema(Schema):
    task_id = ma_fields.Int(required=True)
    comment_text = ma_fields.Str(
        required=True, validate=validate.Length(min=1, max=2000)
    )


class CommentUpdateSchema(Schema):
    comment_text = ma_fields.Str(
        required=True, validate=validate.Length(min=1, max=2000)
    )


# Flask-RESTX models for Swagger documentation
comment_create_model = comments_ns.model(
    "CommentCreate",
    {
        "task_id": fields.Integer(required=True, description="Task ID", example=1),
        "comment_text": fields.String(
            required=True,
            description="Comment text",
            example="This task is progressing well",
        ),
    },
)

comment_update_model = comments_ns.model(
    "CommentUpdate",
    {
        "comment_text": fields.String(
            required=True,
            description="Updated comment text",
            example="Updated comment content",
        )
    },
)

comment_model = comments_ns.model(
    "Comment",
    {
        "id": fields.Integer(description="Comment ID"),
        "task_id": fields.Integer(description="Task ID"),
        "user_id": fields.Integer(description="Author user ID"),
        "comment_text": fields.String(description="Comment text"),
        "created_at": fields.String(description="Creation date"),
        "author_name": fields.String(description="Author full name"),
    },
)


@comments_ns.route("")
class CommentList(Resource):
    @jwt_required()
    @comments_ns.marshal_list_with(comment_model)
    @comments_ns.param("task_id", "Filter by task ID", required=True)
    @comments_ns.response(400, "Task ID required")
    @comments_ns.response(401, "Authentication required")
    @comments_ns.response(403, "Access denied")
    @comments_ns.response(404, "Task not found")
    def get(self):
        """Get comments for a specific task"""
        user_id = get_jwt_identity()
        task_id = request.args.get("task_id", type=int)

        if not task_id:
            comments_ns.abort(400, "Task ID is required")

        # Check if task exists and user has access
        task = Task.query.get(task_id)
        if not task:
            comments_ns.abort(404, "Task not found")

        if not task.can_user_view(user_id):
            comments_ns.abort(403, "Access denied to task")

        # Get comments for the task
        comments = (
            TaskComment.query.filter_by(task_id=task_id)
            .order_by(TaskComment.created_at.asc())
            .all()
        )

        return [comment.to_dict() for comment in comments]

    @jwt_required()
    @comments_ns.expect(comment_create_model)
    @comments_ns.marshal_with(comment_model, code=201)
    @comments_ns.response(400, "Validation error")
    @comments_ns.response(401, "Authentication required")
    @comments_ns.response(403, "Access denied")
    @comments_ns.response(404, "Task not found")
    def post(self):
        """Add a comment to a task"""
        user_id = get_jwt_identity()

        try:
            # Validate input data
            schema = CommentCreateSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            comments_ns.abort(400, f"Validation error: {err.messages}")

        # Check if task exists and user has access
        task = Task.query.get(data["task_id"])
        if not task:
            comments_ns.abort(404, "Task not found")

        if not task.can_user_view(user_id):
            comments_ns.abort(403, "Access denied to task")

        # Create new comment
        comment = TaskComment(
            task_id=data["task_id"], user_id=user_id, comment_text=data["comment_text"]
        )

        db.session.add(comment)
        db.session.commit()

        return comment.to_dict(), 201


@comments_ns.route("/<int:comment_id>")
class CommentDetail(Resource):
    @jwt_required()
    @comments_ns.marshal_with(comment_model)
    @comments_ns.response(401, "Authentication required")
    @comments_ns.response(404, "Comment not found")
    def get(self, comment_id):
        """Get comment details"""
        user_id = get_jwt_identity()

        comment = TaskComment.query.get(comment_id)
        if not comment:
            comments_ns.abort(404, "Comment not found")

        # Check if user has access to the task
        task = Task.query.get(comment.task_id)
        if not task or not task.can_user_view(user_id):
            comments_ns.abort(403, "Access denied")

        return comment.to_dict()

    @jwt_required()
    @comments_ns.expect(comment_update_model)
    @comments_ns.marshal_with(comment_model)
    @comments_ns.response(400, "Validation error")
    @comments_ns.response(401, "Authentication required")
    @comments_ns.response(403, "Access denied")
    @comments_ns.response(404, "Comment not found")
    def put(self, comment_id):
        """Update comment text"""
        user_id = get_jwt_identity()

        comment = TaskComment.query.get(comment_id)
        if not comment:
            comments_ns.abort(404, "Comment not found")

        # Check if user can edit this comment
        if not comment.can_user_edit(user_id):
            comments_ns.abort(403, "Access denied - only comment author can edit")

        try:
            # Validate input data
            schema = CommentUpdateSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            comments_ns.abort(400, f"Validation error: {err.messages}")

        # Update comment
        comment.comment_text = data["comment_text"]
        db.session.commit()

        return comment.to_dict()

    @jwt_required()
    @comments_ns.response(204, "Comment deleted")
    @comments_ns.response(401, "Authentication required")
    @comments_ns.response(403, "Access denied")
    @comments_ns.response(404, "Comment not found")
    def delete(self, comment_id):
        """Delete comment"""
        user_id = get_jwt_identity()

        comment = TaskComment.query.get(comment_id)
        if not comment:
            comments_ns.abort(404, "Comment not found")

        # Check if user can delete this comment
        if not comment.can_user_delete(user_id):
            comments_ns.abort(
                403, "Access denied - insufficient permissions to delete comment"
            )

        db.session.delete(comment)
        db.session.commit()

        return "", 204


@comments_ns.route("/task/<int:task_id>")
class TaskCommentList(Resource):
    @jwt_required()
    @comments_ns.marshal_list_with(comment_model)
    @comments_ns.response(401, "Authentication required")
    @comments_ns.response(403, "Access denied")
    @comments_ns.response(404, "Task not found")
    def get(self, task_id):
        """Get all comments for a specific task (alternative endpoint)"""
        user_id = get_jwt_identity()

        # Check if task exists and user has access
        task = Task.query.get(task_id)
        if not task:
            comments_ns.abort(404, "Task not found")

        if not task.can_user_view(user_id):
            comments_ns.abort(403, "Access denied to task")

        # Get comments for the task
        comments = (
            TaskComment.query.filter_by(task_id=task_id)
            .order_by(TaskComment.created_at.asc())
            .all()
        )

        return [comment.to_dict() for comment in comments]
