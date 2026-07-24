from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from common.decorators import login_required, role_required
from common.models import (
    list_coaches, get_user_by_username, get_coach_by_user_id,
    create_coach, update_coach, archive_coach,
    list_athletes, get_athlete_by_id, create_athlete, update_athlete, archive_athlete,
    log_audit,
)

bp = Blueprint("admin", __name__)


@bp.route("/admin")
@login_required
@role_required("admin")
def admin_panel():
    return render_template("admin.html", coaches=list_coaches())


# --------------------------------------------------------------------
# Coaches
# --------------------------------------------------------------------

@bp.route("/admin/coaches")
@login_required
@role_required("admin")
def admin_coaches():
    return render_template("admin_coaches.html", coaches=list_coaches())


@bp.route("/admin/coaches/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_coach_create():
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
            create_coach(username, password, name, email, specialty,
                         created_by=session["user"]["id"])
            log_audit(session["user"]["username"], "admin", "CREATE_COACH",
                      target_type="USER", details=f"username={username}")
            flash(f"Coach '{name}' created successfully.", "success")
            return redirect(url_for("admin.admin_coaches"))

    return render_template("admin_coach_form.html", coach=None)


@bp.route("/admin/coaches/<username>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_coach_edit(username):
    user = get_user_by_username(username)
    if not user or user["role"] != "coach":
        flash("Coach not found.", "danger")
        return redirect(url_for("admin.admin_coaches"))

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
            log_audit(session["user"]["username"], "admin", "UPDATE_COACH",
                      target_type="USER", target_id=user["id"])
            flash(f"Coach '{name}' updated successfully.", "success")
            return redirect(url_for("admin.admin_coaches"))

    return render_template("admin_coach_form.html", coach={
        "username": username,
        "name": user["name"],
        "email": user["email"],
        "specialty": coach["specialty"] if coach else "",
    })


@bp.route("/admin/coaches/<username>/archive", methods=["POST"])
@login_required
@role_required("admin")
def admin_coach_archive(username):
    user = get_user_by_username(username)
    if not user or user["role"] != "coach":
        flash("Coach not found.", "danger")
        return redirect(url_for("admin.admin_coaches"))

    coach = get_coach_by_user_id(user["id"])
    if not coach:
        flash("Coach not found.", "danger")
        return redirect(url_for("admin.admin_coaches"))

    new_status = not coach["is_archived"]
    archive_coach(coach["id"], new_status)
    log_audit(session["user"]["username"], "admin",
              "ARCHIVE_COACH" if new_status else "UNARCHIVE_COACH",
              target_type="USER", target_id=user["id"])
    status = "archived" if new_status else "unarchived"
    flash(f"Coach '{user['name']}' has been {status}.", "success")
    return redirect(url_for("admin.admin_coaches"))


# --------------------------------------------------------------------
# Athletes (visibility & control across every coach)
# --------------------------------------------------------------------

@bp.route("/admin/athletes")
@login_required
@role_required("admin")
def admin_athletes():
    return render_template("admin_athletes.html", athletes=list_athletes())


@bp.route("/admin/athletes/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_athlete_create():
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
            athlete_id = create_athlete(name, email, phone, dob, sport, int(coach_id),
                                         created_by=session["user"]["id"])
            log_audit(session["user"]["username"], "admin", "CREATE_ATHLETE",
                      target_type="ATHLETE", target_id=athlete_id)
            flash(f"Athlete '{name}' created successfully.", "success")
            return redirect(url_for("admin.admin_athletes"))

    return render_template("admin_athlete_form.html", athlete=None, coaches=coach_choices)


@bp.route("/admin/athletes/<int:athlete_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_athlete_edit(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("admin.admin_athletes"))

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
            log_audit(session["user"]["username"], "admin", "UPDATE_ATHLETE",
                      target_type="ATHLETE", target_id=athlete_id)
            flash(f"Athlete '{name}' updated successfully.", "success")
            return redirect(url_for("admin.admin_athletes"))

    return render_template("admin_athlete_form.html", athlete=athlete, coaches=coach_choices)


@bp.route("/admin/athletes/<int:athlete_id>/archive", methods=["POST"])
@login_required
@role_required("admin")
def admin_athlete_archive(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("admin.admin_athletes"))

    new_status = not athlete["is_archived"]
    archive_athlete(athlete_id, new_status)
    log_audit(session["user"]["username"], "admin",
              "ARCHIVE_ATHLETE" if new_status else "UNARCHIVE_ATHLETE",
              target_type="ATHLETE", target_id=athlete_id)
    status = "archived" if new_status else "unarchived"
    flash(f"Athlete '{athlete['name']}' has been {status}.", "success")
    return redirect(url_for("admin.admin_athletes"))
