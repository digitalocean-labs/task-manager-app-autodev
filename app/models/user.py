from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    created_projects = db.relationship(
        "Project", foreign_keys="Project.owner_id", backref="owner", lazy="dynamic"
    )
    assigned_tasks = db.relationship(
        "Task", foreign_keys="Task.assigned_to", backref="assignee", lazy="dynamic"
    )
    created_tasks = db.relationship(
        "Task", foreign_keys="Task.created_by", backref="creator", lazy="dynamic"
    )
    comments = db.relationship("TaskComment", backref="author", lazy="dynamic")
    project_memberships = db.relationship(
        "ProjectMember", backref="user", lazy="dynamic"
    )

    def __init__(self, username, email, full_name, password):
        self.username = username
        self.email = email
        self.full_name = full_name
        self.set_password(password)

    def set_password(self, password):
        """Set password hash from plain text password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash."""
        return check_password_hash(self.password_hash, password)

    def get_projects(self):
        """Get all projects user has access to."""
        from app.models.project_member import ProjectMember
        from app.models.project import Project

        # Projects owned by user
        owned_projects = Project.query.filter_by(owner_id=self.id).all()

        # Projects user is a member of
        member_projects = (
            db.session.query(Project)
            .join(ProjectMember)
            .filter(
                ProjectMember.user_id == self.id, ProjectMember.project_id == Project.id
            )
            .all()
        )

        # Combine and remove duplicates
        all_projects = list(set(owned_projects + member_projects))
        return all_projects

    def can_access_project(self, project_id):
        """Check if user can access a specific project."""
        from app.models.project_member import ProjectMember
        from app.models.project import Project

        project = Project.query.get(project_id)
        if not project:
            return False

        # Check if user is owner
        if project.owner_id == self.id:
            return True

        # Check if user is a member
        membership = ProjectMember.query.filter_by(
            project_id=project_id, user_id=self.id
        ).first()

        return membership is not None

    def to_dict(self):
        """Convert user object to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
        }

    def __repr__(self):
        return f"<User {self.username}>"
