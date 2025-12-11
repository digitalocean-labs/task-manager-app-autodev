from datetime import datetime
from app import db


class ProjectMember(db.Model):
    __tablename__ = "project_members"

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    role = db.Column(
        db.Enum("owner", "admin", "member", "viewer", name="member_role"),
        default="member",
        nullable=False,
    )
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, project_id, user_id, role="member"):
        self.project_id = project_id
        self.user_id = user_id
        self.role = role

    def update_role(self, new_role):
        """Update member role with validation."""
        valid_roles = ["owner", "admin", "member", "viewer"]
        if new_role in valid_roles:
            self.role = new_role
            return True
        return False

    def can_manage_tasks(self):
        """Check if member can create/edit/delete tasks."""
        return self.role in ["owner", "admin", "member"]

    def can_manage_members(self):
        """Check if member can add/remove project members."""
        return self.role in ["owner", "admin"]

    def can_edit_project(self):
        """Check if member can edit project details."""
        return self.role in ["owner", "admin"]

    def can_delete_project(self):
        """Check if member can delete the project."""
        return self.role == "owner"

    def to_dict(self):
        """Convert project member object to dictionary."""
        return {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat(),
            "user_name": self.user.full_name if self.user else "Unknown",
            "user_email": self.user.email if self.user else "Unknown",
        }

    @staticmethod
    def get_user_projects(user_id, role=None):
        """Get all projects for a user with optional role filter."""
        query = ProjectMember.query.filter_by(user_id=user_id)

        if role:
            query = query.filter_by(role=role)

        return query.all()

    @staticmethod
    def get_project_members(project_id, role=None):
        """Get all members for a project with optional role filter."""
        query = ProjectMember.query.filter_by(project_id=project_id)

        if role:
            query = query.filter_by(role=role)

        return query.all()

    def __repr__(self):
        return f"<ProjectMember User:{self.user_id} Project:{self.project_id} Role:{self.role}>"
