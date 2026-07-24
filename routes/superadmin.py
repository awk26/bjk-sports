from flask import Blueprint, render_template, request, redirect, url_for, flash

from common.decorators import login_required, role_required
from common.models import (
    list_users, list_coaches, list_athletes, get_athlete_by_id,
    get_user_by_username, get_coach_by_user_id,
    create_user, update_user, update_user_password, archive_user,
    create_coach, update_coach, archive_coach,
    create_athlete, update_athlete, archive_athlete,
    log_audit,
)

bp = Blueprint("superadmin", __name__, url_prefix="/superadmin")


# --------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------

@bp.route("/")
@login_required
@role_required("superadmin")
def superadmin_panel():
    return redirect(url_for("superadmin.superadmin_admins"))


# --------------------------------------------------------------------
# Admins
# --------------------------------------------------------------------

@bp.route("/admins")
@login_required
@role_required("superadmin")
def superadmin_admins():
    return render_template("superadmin_admins.html", admins=list_users(role="admin"))


@bp.route("/admins/create", methods=["GET", "POST"])
@login_required
@role_required("superadmin")
def superadmin_admin_create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()

        if not username or not password or not name:
            flash("Username, password, and name are required.", "danger")
        elif get_user_by_username(username):
            flash("Username already exists.", "danger")
        else:
            create_user(username, password, "admin", name, email)
            log_audit("superadmin", "superadmin", "CREATE_ADMIN",
                      target_type="USER", details=f"username={username}")
            flash(f"Admin '{name}' created successfully.", "success")
            return redirect(url_for("superadmin.superadmin_admins"))

    return render_template("superadmin_admin_form.html", admin=None)


@bp.route("/admins/<username>/edit", methods=["GET", "POST"])
@login_required
@role_required("superadmin")
def superadmin_admin_edit(username):
    user = get_user_by_username(username)
    if not user or user["role"] != "admin":
        flash("Admin not found.", "danger")
        return redirect(url_for("superadmin.superadmin_admins"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name:
            flash("Name is required.", "danger")
        else:
            update_user(user["id"], name, email)
            if password:
                update_user_password(user["id"], password)
            log_audit("superadmin", "superadmin", "UPDATE_ADMIN",
                      target_type="USER", target_id=user["id"])
            flash(f"Admin '{name}' updated successfully.", "success")
            return redirect(url_for("superadmin.superadmin_admins"))

    return render_template("superadmin_admin_form.html", admin={
        "username": username,
        "name": user["name"],
        "email": user["email"],
    })


@bp.route("/admins/<username>/archive", methods=["POST"])
@login_required
@role_required("superadmin")
def superadmin_admin_archive(username):
    user = get_user_by_username(username)
    if not user or user["role"] != "admin":
        flash("Admin not found.", "danger")
        return redirect(url_for("superadmin.superadmin_admins"))

    new_status = not user["is_archived"]
    archive_user(user["id"], new_status)
    log_audit("superadmin", "superadmin",
              "ARCHIVE_ADMIN" if new_status else "UNARCHIVE_ADMIN",
              target_type="USER", target_id=user["id"])
    status = "archived" if new_status else "unarchived"
    flash(f"Admin '{user['name']}' has been {status}.", "success")
    return redirect(url_for("superadmin.superadmin_admins"))


# --------------------------------------------------------------------
# Coaches (super admin has the same rights admin.py exposes to admins)
# --------------------------------------------------------------------

@bp.route("/coaches")
@login_required
@role_required("superadmin")
def superadmin_coaches():
    return render_template("superadmin_coaches.html", coaches=list_coaches())


@bp.route("/coaches/create", methods=["GET", "POST"])
@login_required
@role_required("superadmin")
def superadmin_coach_create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        specialty = request.form.get("specialty", "").strip()

        if not username or not password or not name:
            flash("Username, password, and name are required.", "danger")
        elif get_user_by_username(username):
            flash("Username already exists.", "danger")
        else:
            create_coach(username, password, name, email, specialty)
            log_audit("superadmin", "superadmin", "CREATE_COACH",
                      target_type="USER", details=f"username={username}")
            flash(f"Coach '{name}' created successfully.", "success")
            return redirect(url_for("superadmin.superadmin_coaches"))

    return render_template("superadmin_coach_form.html", coach=None)


@bp.route("/coaches/<username>/edit", methods=["GET", "POST"])
@login_required
@role_required("superadmin")
def superadmin_coach_edit(username):
    user = get_user_by_username(username)
    if not user or user["role"] != "coach":
        flash("Coach not found.", "danger")
        return redirect(url_for("superadmin.superadmin_coaches"))

    coach = get_coach_by_user_id(user["id"])

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        specialty = request.form.get("specialty", "").strip()
        password = request.form.get("password", "")

        if not name:
            flash("Name is required.", "danger")
        else:
            update_coach(coach["id"], user["id"], name, email, specialty, password or None)
            log_audit("superadmin", "superadmin", "UPDATE_COACH",
                      target_type="USER", target_id=user["id"])
            flash(f"Coach '{name}' updated successfully.", "success")
            return redirect(url_for("superadmin.superadmin_coaches"))

    return render_template("superadmin_coach_form.html", coach={
        "username": username,
        "name": user["name"],
        "email": user["email"],
        "specialty": coach["specialty"] if coach else "",
    })


@bp.route("/coaches/<username>/archive", methods=["POST"])
@login_required
@role_required("superadmin")
def superadmin_coach_archive(username):
    user = get_user_by_username(username)
    if not user or user["role"] != "coach":
        flash("Coach not found.", "danger")
        return redirect(url_for("superadmin.superadmin_coaches"))

    coach = get_coach_by_user_id(user["id"])
    if not coach:
        flash("Coach not found.", "danger")
        return redirect(url_for("superadmin.superadmin_coaches"))

    new_status = not coach["is_archived"]
    archive_coach(coach["id"], new_status)
    log_audit("superadmin", "superadmin",
              "ARCHIVE_COACH" if new_status else "UNARCHIVE_COACH",
              target_type="USER", target_id=user["id"])
    status = "archived" if new_status else "unarchived"
    flash(f"Coach '{user['name']}' has been {status}.", "success")
    return redirect(url_for("superadmin.superadmin_coaches"))


# --------------------------------------------------------------------
# Athletes (visibility & control across every coach)
# --------------------------------------------------------------------

@bp.route("/athletes")
@login_required
@role_required("superadmin")
def superadmin_athletes():
    return render_template("superadmin_athletes.html", athletes=list_athletes())


@bp.route("/athletes/create", methods=["GET", "POST"])
@login_required
@role_required("superadmin")
def superadmin_athlete_create():
    coach_choices = [(c["id"], c["name"]) for c in list_coaches(is_archived=False)]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        dob = request.form.get("dob", "").strip()
        sport = request.form.get("sport", "").strip()
        coach_id = request.form.get("coach_id", "").strip()

        valid_coach_ids = {str(cid) for cid, _ in coach_choices}
        if not name or not coach_id:
            flash("Athlete name and coach are required.", "danger")
        elif coach_id not in valid_coach_ids:
            flash("Selected coach is invalid.", "danger")
        else:
            create_athlete(name, email, phone, dob, sport, int(coach_id))
            flash(f"Athlete '{name}' created successfully.", "success")
            return redirect(url_for("superadmin.superadmin_athletes"))

    return render_template("superadmin_athlete_form.html", athlete=None, coaches=coach_choices)


@bp.route("/athletes/<int:athlete_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("superadmin")
def superadmin_athlete_edit(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("superadmin.superadmin_athletes"))

    coach_choices = [(c["id"], c["name"]) for c in list_coaches(is_archived=False)]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        dob = request.form.get("dob", "").strip()
        sport = request.form.get("sport", "").strip()
        coach_id = request.form.get("coach_id", "").strip()

        valid_coach_ids = {str(cid) for cid, _ in coach_choices}
        if not name or not coach_id:
            flash("Athlete name and coach are required.", "danger")
        elif coach_id not in valid_coach_ids:
            flash("Selected coach is invalid.", "danger")
        else:
            update_athlete(athlete_id, name, email, phone, dob, sport, int(coach_id))
            flash(f"Athlete '{name}' updated successfully.", "success")
            return redirect(url_for("superadmin.superadmin_athletes"))

    return render_template("superadmin_athlete_form.html", athlete=athlete, coaches=coach_choices)


@bp.route("/athletes/<int:athlete_id>/archive", methods=["POST"])
@login_required
@role_required("superadmin")
def superadmin_athlete_archive(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("superadmin.superadmin_athletes"))

    new_status = not athlete["is_archived"]
    archive_athlete(athlete_id, new_status)
    status = "archived" if new_status else "unarchived"
    flash(f"Athlete '{athlete['name']}' has been {status}.", "success")
    return redirect(url_for("superadmin.superadmin_athletes"))
