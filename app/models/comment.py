from datetime import datetime
from app import db


class TaskComment(db.Model):
    __tablename__ = "task_comments"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, task_id, user_id, comment_text):
        self.task_id = task_id
        self.user_id = user_id
        self.comment_text = comment_text

    def can_user_edit(self, user_id):
        """Check if user can edit this comment."""
        return self.user_id == user_id

    def can_user_delete(self, user_id):
        """Check if user can delete this comment."""
        # Comment author can delete
        if self.user_id == user_id:
            return True

        # Task creator can delete comments
        from app.models.task import Task

        task = Task.query.get(self.task_id)
        if task and task.created_by == user_id:
            return True

        # Project owner can delete comments
        if task and task.project:
            return task.project.owner_id == user_id

        return False

    def to_dict(self):
        """Convert comment object to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "comment_text": self.comment_text,
            "created_at": self.created_at.isoformat(),
            "author_name": self.author.full_name if self.author else "Unknown",
        }

    def __repr__(self):
        return f"<TaskComment {self.id} on Task {self.task_id}>"
