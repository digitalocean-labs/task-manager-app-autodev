from marshmallow import validate, ValidationError
from email_validator import validate_email, EmailNotValidError
import re


class CustomValidators:
    """Custom validation functions for the API"""

    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not username:
            raise ValidationError("Username is required")

        if len(username) < 3 or len(username) > 80:
            raise ValidationError("Username must be between 3 and 80 characters")

        # Username should contain only alphanumeric characters and underscores
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            raise ValidationError(
                "Username can only contain letters, numbers, and underscores"
            )

        return username

    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if not password:
            raise ValidationError("Password is required")

        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")

        if len(password) > 128:
            raise ValidationError("Password must be less than 128 characters")

        # Check for at least one letter and one number
        if not re.search(r"[A-Za-z]", password):
            raise ValidationError("Password must contain at least one letter")

        if not re.search(r"[0-9]", password):
            raise ValidationError("Password must contain at least one number")

        return password

    @staticmethod
    def validate_email_address(email):
        """Validate email format"""
        if not email:
            raise ValidationError("Email is required")

        try:
            # Use email-validator library for robust email validation
            valid_email = validate_email(email)
            return valid_email.email
        except EmailNotValidError as e:
            raise ValidationError(f"Invalid email format: {str(e)}")

    @staticmethod
    def validate_project_name(name):
        """Validate project name"""
        if not name or not name.strip():
            raise ValidationError("Project name is required")

        if len(name.strip()) > 200:
            raise ValidationError("Project name must be less than 200 characters")

        return name.strip()

    @staticmethod
    def validate_task_title(title):
        """Validate task title"""
        if not title or not title.strip():
            raise ValidationError("Task title is required")

        if len(title.strip()) > 200:
            raise ValidationError("Task title must be less than 200 characters")

        return title.strip()


def validate_enum_field(field_name, value, allowed_values):
    """Validate enum field values"""
    if value not in allowed_values:
        raise ValidationError(
            f"{field_name} must be one of: {', '.join(allowed_values)}"
        )
    return value


def validate_positive_integer(value):
    """Validate positive integer"""
    if not isinstance(value, int) or value <= 0:
        raise ValidationError("Value must be a positive integer")
    return value


def validate_optional_positive_integer(value):
    """Validate optional positive integer (can be None)"""
    if value is not None:
        return validate_positive_integer(value)
    return value
