from flask import jsonify
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended.exceptions import JWTExtendedException
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Register error handlers for the Flask application"""

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle marshmallow validation errors"""
        logger.warning(f"Validation error: {error.messages}")
        return (
            jsonify(
                {
                    "error": "Validation Error",
                    "message": "The request data is invalid",
                    "details": error.messages,
                }
            ),
            400,
        )

    @app.errorhandler(JWTExtendedException)
    def handle_jwt_error(error):
        """Handle JWT-related errors"""
        logger.warning(f"JWT error: {str(error)}")
        return jsonify({"error": "Authentication Error", "message": str(error)}), 401

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        """Handle database errors"""
        logger.error(f"Database error: {str(error)}")
        return (
            jsonify(
                {"error": "Database Error", "message": "A database error occurred"}
            ),
            500,
        )

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": "The requested resource was not found",
                }
            ),
            404,
        )

    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle 403 errors"""
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You do not have permission to access this resource",
                }
            ),
            403,
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 errors"""
        return (
            jsonify(
                {
                    "error": "Method Not Allowed",
                    "message": "The requested method is not allowed for this resource",
                }
            ),
            405,
        )

    @app.errorhandler(409)
    def handle_conflict(error):
        """Handle 409 conflicts"""
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": "The request conflicts with the current state of the resource",
                }
            ),
            409,
        )

    @app.errorhandler(422)
    def handle_unprocessable_entity(error):
        """Handle 422 errors"""
        return (
            jsonify(
                {
                    "error": "Unprocessable Entity",
                    "message": "The request was well-formed but contains semantic errors",
                }
            ),
            422,
        )

    @app.errorhandler(429)
    def handle_rate_limit_exceeded(error):
        """Handle rate limit errors"""
        return (
            jsonify(
                {
                    "error": "Rate Limit Exceeded",
                    "message": "Too many requests. Please try again later.",
                }
            ),
            429,
        )

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {str(error)}")
        return (
            jsonify(
                {
                    "error": "Internal Server Error",
                    "message": "An internal server error occurred",
                }
            ),
            500,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle other HTTP exceptions"""
        return jsonify({"error": error.name, "message": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle any unhandled exceptions"""
        logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
        return (
            jsonify(
                {
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                }
            ),
            500,
        )


class APIError(Exception):
    """Custom API error class"""

    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """Convert error to dictionary"""
        error_dict = {"error": "API Error", "message": self.message}
        if self.payload:
            error_dict.update(self.payload)
        return error_dict


class AuthenticationError(APIError):
    """Authentication-related error"""

    def __init__(self, message="Authentication required"):
        super().__init__(message, status_code=401)


class AuthorizationError(APIError):
    """Authorization-related error"""

    def __init__(self, message="Access denied"):
        super().__init__(message, status_code=403)


class NotFoundError(APIError):
    """Resource not found error"""

    def __init__(self, message="Resource not found"):
        super().__init__(message, status_code=404)


class ConflictError(APIError):
    """Conflict error"""

    def __init__(self, message="Resource conflict"):
        super().__init__(message, status_code=409)
