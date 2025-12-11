from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.frontend.utils import api_request

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    """Redirect to dashboard if logged in, otherwise to login"""
    if session.get("access_token"):
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login page"""
    if session.get("access_token"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("auth/login.html")

        # Call login API
        status_code, response = api_request(
            "POST", "/auth/login", {"username": username, "password": password}
        )

        if status_code == 200 and response:
            # Store tokens and user info in session
            session["access_token"] = response["access_token"]
            session["refresh_token"] = response["refresh_token"]
            session["user"] = response["user"]

            flash(f'Welcome back, {response["user"]["full_name"]}!', "success")

            # Redirect to next page or dashboard
            next_page = request.args.get("next")
            return (
                redirect(next_page)
                if next_page
                else redirect(url_for("dashboard.index"))
            )
        else:
            error_msg = (
                response.get("message", "Login failed")
                if response
                else "Connection error"
            )
            flash(error_msg, "error")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration page"""
    if session.get("access_token"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        full_name = request.form.get("full_name")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validation
        if not all([username, email, full_name, password, confirm_password]):
            flash("Please fill in all fields.", "error")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html")

        # Call registration API
        status_code, response = api_request(
            "POST",
            "/auth/register",
            {
                "username": username,
                "email": email,
                "full_name": full_name,
                "password": password,
            },
        )

        if status_code == 201 and response:
            # Store tokens and user info in session
            session["access_token"] = response["access_token"]
            session["refresh_token"] = response["refresh_token"]
            session["user"] = response["user"]

            flash(
                f'Account created successfully! Welcome, {response["user"]["full_name"]}!',
                "success",
            )
            return redirect(url_for("dashboard.index"))
        else:
            error_msg = (
                response.get("message", "Registration failed")
                if response
                else "Connection error"
            )
            flash(error_msg, "error")

    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    """User logout"""
    if session.get("access_token"):
        # Call logout API (optional, as we're clearing session anyway)
        api_request("POST", "/auth/logout")

    # Clear session
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """User profile page"""
    if not session.get("access_token"):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")

        if not full_name or not email:
            flash("Please fill in all fields.", "error")
            return render_template("auth/profile.html")

        # Call profile update API
        status_code, response = api_request(
            "PUT", "/auth/profile", {"full_name": full_name, "email": email}
        )

        if status_code == 200 and response:
            # Update user info in session
            session["user"] = response
            flash("Profile updated successfully!", "success")
        else:
            error_msg = (
                response.get("message", "Profile update failed")
                if response
                else "Connection error"
            )
            flash(error_msg, "error")

    # Get current user profile
    status_code, user_data = api_request("GET", "/auth/profile")

    if status_code == 200 and user_data:
        return render_template("auth/profile.html", user=user_data)
    else:
        flash("Unable to load profile information.", "error")
        return redirect(url_for("dashboard.index"))
