from datetime import datetime
from app import db


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    tasks = db.relationship(
        "Task", backref="project", lazy="dynamic", cascade="all, delete-orphan"
    )
    members = db.relationship(
        "ProjectMember", backref="project", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __init__(self, name, description, owner_id):
        self.name = name
        self.description = description
        self.owner_id = owner_id

    def get_members(self):
        """Get all members of the project including owner."""
        from app.models.user import User
        from app.models.project_member import ProjectMember

        # Get owner
        owner = User.query.get(self.owner_id)
        members_list = [owner] if owner else []

        # Get project members
        member_users = (
            db.session.query(User)
            .join(ProjectMember)
            .filter(
                ProjectMember.project_id == self.id, ProjectMember.user_id == User.id
            )
            .all()
        )

        # Combine and remove duplicates
        all_members = []
        added_ids = set()

        for member in members_list + member_users:
            if member.id not in added_ids:
                all_members.append(member)
                added_ids.add(member.id)

        return all_members

    def get_member_role(self, user_id):
        """Get user's role in the project."""
        from app.models.project_member import ProjectMember

        # Check if user is owner
        if self.owner_id == user_id:
            return "owner"

        # Check project membership
        membership = ProjectMember.query.filter_by(
            project_id=self.id, user_id=user_id
        ).first()

        return membership.role if membership else None

    def add_member(self, user_id, role="member"):
        """Add a user as a project member."""
        from app.models.project_member import ProjectMember

        # Don't add owner as member
        if self.owner_id == user_id:
            return False

        # Check if already a member
        existing = ProjectMember.query.filter_by(
            project_id=self.id, user_id=user_id
        ).first()

        if existing:
            return False

        # Add new member
        member = ProjectMember(project_id=self.id, user_id=user_id, role=role)
        db.session.add(member)
        return True

    def remove_member(self, user_id):
        """Remove a user from project members."""
        from app.models.project_member import ProjectMember

        # Can't remove owner
        if self.owner_id == user_id:
            return False

        membership = ProjectMember.query.filter_by(
            project_id=self.id, user_id=user_id
        ).first()

        if membership:
            db.session.delete(membership)
            return True

        return False

    def get_task_stats(self):
        """Get task statistics for the project."""
        from app.models.task import Task

        total_tasks = self.tasks.count()
        completed_tasks = self.tasks.filter_by(status="completed").count()
        in_progress_tasks = self.tasks.filter_by(status="in_progress").count()
        pending_tasks = self.tasks.filter_by(status="pending").count()

        return {
            "total": total_tasks,
            "completed": completed_tasks,
            "in_progress": in_progress_tasks,
            "pending": pending_tasks,
            "completion_rate": (completed_tasks / total_tasks * 100)
            if total_tasks > 0
            else 0,
        }

    def to_dict(self, include_stats=False):
        """Convert project object to dictionary."""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
        }

        if include_stats:
            data["stats"] = self.get_task_stats()

        return data

    def __repr__(self):
        return f"<Project {self.name}>"
