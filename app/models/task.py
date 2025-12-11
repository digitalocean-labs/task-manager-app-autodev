from datetime import datetime
from app import db


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(
        db.Enum("pending", "in_progress", "completed", "cancelled", name="task_status"),
        default="pending",
        nullable=False,
        index=True,
    )
    priority = db.Column(
        db.Enum("low", "medium", "high", "critical", name="task_priority"),
        default="medium",
        nullable=False,
        index=True,
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True
    )
    assigned_to = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    comments = db.relationship(
        "TaskComment", backref="task", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        title,
        description,
        project_id,
        created_by,
        assigned_to=None,
        priority="medium",
        due_date=None,
    ):
        self.title = title
        self.description = description
        self.project_id = project_id
        self.created_by = created_by
        self.assigned_to = assigned_to
        self.priority = priority
        self.due_date = due_date

    def update_status(self, new_status):
        """Update task status with validation."""
        valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
        if new_status in valid_statuses:
            self.status = new_status
            self.updated_at = datetime.utcnow()
            return True
        return False

    def assign_to_user(self, user_id):
        """Assign task to a user."""
        self.assigned_to = user_id
        self.updated_at = datetime.utcnow()

    def unassign(self):
        """Remove task assignment."""
        self.assigned_to = None
        self.updated_at = datetime.utcnow()

    def is_overdue(self):
        """Check if task is overdue."""
        if not self.due_date:
            return False
        return datetime.utcnow() > self.due_date and self.status not in [
            "completed",
            "cancelled",
        ]

    def get_comments_count(self):
        """Get number of comments on the task."""
        return self.comments.count()

    def can_user_edit(self, user_id):
        """Check if user can edit this task."""
        # Task creator, assignee, or project owner can edit
        if user_id in [self.created_by, self.assigned_to]:
            return True

        # Check if user is project owner
        from app.models.project import Project

        project = Project.query.get(self.project_id)
        return project and project.owner_id == user_id

    def can_user_view(self, user_id):
        """Check if user can view this task."""
        # Check if user has access to the project
        from app.models.user import User

        user = User.query.get(user_id)
        return user and user.can_access_project(self.project_id)

    def to_dict(self, include_comments=False):
        """Convert task object to dictionary."""
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "project_id": self.project_id,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_overdue": self.is_overdue(),
            "comments_count": self.get_comments_count(),
        }

        if include_comments:
            data["comments"] = [comment.to_dict() for comment in self.comments.all()]

        return data

    @staticmethod
    def get_tasks_by_filters(
        project_id=None,
        assigned_to=None,
        status=None,
        priority=None,
        limit=None,
        offset=None,
    ):
        """Get tasks with optional filters."""
        query = Task.query

        if project_id:
            query = query.filter_by(project_id=project_id)
        if assigned_to:
            query = query.filter_by(assigned_to=assigned_to)
        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)

        # Order by priority (critical first) and creation date
        priority_order = db.case(
            (Task.priority == "critical", 0),
            (Task.priority == "high", 1),
            (Task.priority == "medium", 2),
            (Task.priority == "low", 3),
        )
        query = query.order_by(priority_order, Task.created_at.desc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def __repr__(self):
        return f"<Task {self.title}>"
