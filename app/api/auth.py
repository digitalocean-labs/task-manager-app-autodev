from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from marshmallow import Schema, fields as ma_fields, validate, ValidationError
from email_validator import validate_email, EmailNotValidError
from app import db
from app.models.user import User

auth_ns = Namespace("auth", description="Authentication operations")


# Marshmallow schemas for input validation
class UserRegistrationSchema(Schema):
    username = ma_fields.Str(required=True, validate=validate.Length(min=3, max=80))
    email = ma_fields.Email(required=True)
    full_name = ma_fields.Str(required=True, validate=validate.Length(min=1, max=200))
    password = ma_fields.Str(required=True, validate=validate.Length(min=6))


class UserLoginSchema(Schema):
    username = ma_fields.Str(required=True)
    password = ma_fields.Str(required=True)


class UserProfileUpdateSchema(Schema):
    full_name = ma_fields.Str(validate=validate.Length(min=1, max=200))
    email = ma_fields.Email()


# Flask-RESTX models for Swagger documentation
user_registration_model = auth_ns.model(
    "UserRegistration",
    {
        "username": fields.String(
            required=True, description="Username (3-80 characters)", example="johndoe"
        ),
        "email": fields.String(
            required=True, description="Email address", example="john@example.com"
        ),
        "full_name": fields.String(
            required=True, description="Full name", example="John Doe"
        ),
        "password": fields.String(
            required=True,
            description="Password (minimum 6 characters)",
            example="password123",
        ),
    },
)

user_login_model = auth_ns.model(
    "UserLogin",
    {
        "username": fields.String(
            required=True, description="Username", example="johndoe"
        ),
        "password": fields.String(
            required=True, description="Password", example="password123"
        ),
    },
)

user_profile_model = auth_ns.model(
    "UserProfile",
    {
        "id": fields.Integer(description="User ID"),
        "username": fields.String(description="Username"),
        "email": fields.String(description="Email address"),
        "full_name": fields.String(description="Full name"),
        "created_at": fields.String(description="Account creation date"),
        "is_active": fields.Boolean(description="Account status"),
    },
)

token_model = auth_ns.model(
    "TokenResponse",
    {
        "access_token": fields.String(description="JWT access token"),
        "refresh_token": fields.String(description="JWT refresh token"),
        "user": fields.Nested(
            user_profile_model, description="User profile information"
        ),
    },
)

user_update_model = auth_ns.model(
    "UserUpdate",
    {
        "full_name": fields.String(description="Full name"),
        "email": fields.String(description="Email address"),
    },
)


@auth_ns.route("/register")
class UserRegistration(Resource):
    @auth_ns.expect(user_registration_model)
    @auth_ns.marshal_with(token_model, code=201)
    @auth_ns.response(400, "Validation error")
    @auth_ns.response(409, "User already exists")
    def post(self):
        """Register a new user"""
        try:
            # Validate input data
            schema = UserRegistrationSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            auth_ns.abort(400, f"Validation error: {err.messages}")

        # Check if user already exists
        if User.query.filter_by(username=data["username"]).first():
            auth_ns.abort(409, "Username already exists")

        if User.query.filter_by(email=data["email"]).first():
            auth_ns.abort(409, "Email already exists")

        # Create new user
        user = User(
            username=data["username"],
            email=data["email"],
            full_name=data["full_name"],
            password=data["password"],
        )

        db.session.add(user)
        db.session.commit()

        # Generate tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict(),
        }, 201


@auth_ns.route("/login")
class UserLogin(Resource):
    @auth_ns.expect(user_login_model)
    @auth_ns.marshal_with(token_model)
    @auth_ns.response(401, "Invalid credentials")
    def post(self):
        """Login user and return JWT tokens"""
        try:
            # Validate input data
            schema = UserLoginSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            auth_ns.abort(400, f"Validation error: {err.messages}")

        # Find user and verify password
        user = User.query.filter_by(username=data["username"]).first()

        if not user or not user.check_password(data["password"]):
            auth_ns.abort(401, "Invalid username or password")

        if not user.is_active:
            auth_ns.abort(401, "Account is deactivated")

        # Generate tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict(),
        }


@auth_ns.route("/profile")
class UserProfile(Resource):
    @jwt_required()
    @auth_ns.marshal_with(user_profile_model)
    @auth_ns.response(401, "Authentication required")
    def get(self):
        """Get current user profile"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            auth_ns.abort(404, "User not found")

        return user.to_dict()

    @jwt_required()
    @auth_ns.expect(user_update_model)
    @auth_ns.marshal_with(user_profile_model)
    @auth_ns.response(400, "Validation error")
    @auth_ns.response(401, "Authentication required")
    @auth_ns.response(409, "Email already exists")
    def put(self):
        """Update current user profile"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            auth_ns.abort(404, "User not found")

        try:
            # Validate input data
            schema = UserProfileUpdateSchema()
            data = schema.load(request.json)
        except ValidationError as err:
            auth_ns.abort(400, f"Validation error: {err.messages}")

        # Update fields if provided
        if "email" in data:
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=data["email"]).first()
            if existing_user and existing_user.id != user.id:
                auth_ns.abort(409, "Email already exists")
            user.email = data["email"]

        if "full_name" in data:
            user.full_name = data["full_name"]

        db.session.commit()

        return user.to_dict()


@auth_ns.route("/refresh")
class TokenRefresh(Resource):
    @jwt_required(refresh=True)
    @auth_ns.marshal_with(fields.Raw, code=200)
    @auth_ns.response(401, "Invalid refresh token")
    def post(self):
        """Refresh access token using refresh token"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or not user.is_active:
            auth_ns.abort(401, "Invalid user or account deactivated")

        new_access_token = create_access_token(identity=user_id)

        return {"access_token": new_access_token}


@auth_ns.route("/logout")
class UserLogout(Resource):
    @jwt_required()
    @auth_ns.response(200, "Successfully logged out")
    @auth_ns.response(401, "Authentication required")
    def post(self):
        """Logout user (client should discard tokens)"""
        # In a production environment, you might want to blacklist the token
        # For now, we'll just return a success message
        return {"message": "Successfully logged out"}
