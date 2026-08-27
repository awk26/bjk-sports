from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from common.decorators import login_required
from common.models import (
    verify_user, verify_superadmin, get_user_by_username,
    get_coach_by_user_id, get_athlete_by_user_id, create_reset_token, get_reset_token,
    mark_reset_token_used, update_user_password,
)

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Super admin — hardcoded credentials, checked first, never in the DB.
        if verify_superadmin(username, password):
            session.permanent = True
            session["user"] = {
                "username": username,
                "role": "superadmin",
                "name": "Super Admin",
            }
            flash("Welcome back, Super Admin!", "success")
            return redirect(url_for("dashboard"))

        user = verify_user(username, password)
        if user:
            session_user = {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "name": user["name"],
            }
            if user["role"] == "coach":
                coach = get_coach_by_user_id(user["id"])
                if coach:
                    session_user["coach_id"] = coach["id"]

            elif user["role"] == "athlete":
                athlete = get_athlete_by_user_id(user["id"])
                if athlete:
                    session_user["athlete_id"] = athlete["id"]

            session.permanent = True
            session["user"] = session_user
            flash(f"Welcome back, {user['name']}!", "success")
            if user["role"] == "athlete":
                return redirect(url_for("athlete.athlete_dashboard"))
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        user = get_user_by_username(username)

        if user:
            create_reset_token(user["id"])
            flash(f"Password reset link has been sent to {user['email']}.", "info")
        else:
            flash("If that username exists, a reset link has been sent.", "info")

        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_data = get_reset_token(token)
    if not token_data:
        flash("Invalid or expired reset token.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not new_password or len(new_password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "danger")
        else:
            update_user_password(token_data["user_id"], new_password)
            mark_reset_token_used(token)
            flash("Password has been reset successfully. Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)
