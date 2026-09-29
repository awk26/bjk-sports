from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from common.decorators import login_required
from common.mailer import send_password_otp
from common.models import (
    verify_user, verify_superadmin, get_user_by_username,
    get_coach_by_user_id, get_athlete_by_user_id, create_reset_token, get_reset_token,
    mark_reset_token_used, update_user_password,
    get_user_by_email, create_password_otp, verify_password_otp,
    OTP_VALID_MINUTES,
)


bp = Blueprint("auth", __name__)

# The whole email -> OTP -> new password journey has to finish inside this
# window, independently of the OTP's own expiry.
RESET_FLOW_MINUTES = 20
MIN_PASSWORD_LENGTH = 6


def _flow_state():
    """The in-progress reset flow from the session, or None when there isn't
    one (or it has aged out)."""
    state = session.get("pwd_reset")
    if not state:
        return None
    try:
        started = datetime.fromisoformat(state["started"])
    except (KeyError, TypeError, ValueError):
        session.pop("pwd_reset", None)
        return None
    if datetime.now() - started > timedelta(minutes=RESET_FLOW_MINUTES):
        session.pop("pwd_reset", None)
        return None
    return state


def _begin_flow(email, user_id):
    """user_id is None when the email matched no account -- the flow still
    starts so the next page looks identical either way, and simply never
    accepts a code."""
    session["pwd_reset"] = {
        "email": email,
        "user_id": user_id,
        "verified": False,
        "started": datetime.now().isoformat(),
    }


def _end_flow():
    session.pop("pwd_reset", None)


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
    """Step 1 -- ask for the email address and send a one-time code.

    The response is deliberately identical whether or not the email is
    registered, so this page can't be used to discover who has an account.
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            flash("Enter your email address.", "danger")
            return render_template("forgot_password.html")

        user = get_user_by_email(email)
        print("User found for email:", user)  # Debugging line
        if user:
            otp = create_password_otp(user["id"])
            print("OTP generated:", otp)  # Debugging line
            if otp:
                print("Sending OTP to email:", user["email"])  # Debugging line
                send_password_otp(user["email"] or email, otp, OTP_VALID_MINUTES)
            # A failure to store or send is logged, not shown -- telling the
            # visitor would reveal that the address exists.

        _begin_flow(email, user["id"] if user else None)
        flash(f"If {email} is registered, a {OTP_VALID_MINUTES}-minute "
              "verification code is on its way.", "info")
        return redirect(url_for("auth.verify_otp"))

    return render_template("forgot_password.html")


@bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    """Step 2 -- check the emailed code."""
    state = _flow_state()
    if not state:
        flash("Your password reset session expired. Please start again.", "warning")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        submitted = request.form.get("otp", "").strip()

        # No account for that address: behave exactly like a wrong code so
        # the outcome doesn't disclose whether the email is registered.
        if not state.get("user_id"):
            flash("That code is no longer valid. Please request a new one.", "danger")
            return render_template("verify_otp.html", email=state["email"])

        ok, message = verify_password_otp(state["user_id"], submitted)
        if ok:
            state["verified"] = True
            session["pwd_reset"] = state
            return redirect(url_for("auth.reset_password_otp"))

        flash(message, "danger")

    return render_template("verify_otp.html", email=state["email"])


@bp.route("/reset-password", methods=["GET", "POST"])
def reset_password_otp():
    """Step 3 -- set the new password. Reachable only once the OTP for this
    session has actually been verified."""
    state = _flow_state()
    if not state:
        flash("Your password reset session expired. Please start again.", "warning")
        return redirect(url_for("auth.forgot_password"))

    if not state.get("verified") or not state.get("user_id"):
        flash("Please verify the code we emailed you first.", "warning")
        return redirect(url_for("auth.verify_otp"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(new_password) < MIN_PASSWORD_LENGTH:
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "danger")
        else:
            update_user_password(state["user_id"], new_password)
            _end_flow()
            flash("Your password has been updated. Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("reset_password_otp.html", email=state["email"])


@bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    """Issue a new code for the flow already in progress. Issuing one
    invalidates the previous code."""
    state = _flow_state()
    if not state:
        flash("Your password reset session expired. Please start again.", "warning")
        return redirect(url_for("auth.forgot_password"))

    if state.get("user_id"):
        otp = create_password_otp(state["user_id"])
        if otp:
            send_password_otp(state["email"], otp, OTP_VALID_MINUTES)

    # Same message either way, for the same non-disclosure reason.
    flash("A new verification code has been sent.", "info")
    return redirect(url_for("auth.verify_otp"))


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
