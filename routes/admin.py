from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from common.decorators import login_required, role_required
from common.validators import (
    missing_athlete_fields, missing_coach_fields, missing_fields_message,
)
from common.models import (
    list_coaches, get_user_by_username, get_coach_by_user_id,
    create_coach, update_coach, archive_coach,
    list_athletes, get_athlete_by_id, create_athlete, update_athlete, archive_athlete,
    list_sports, get_sport_by_id, get_sport_by_name, create_sport, update_sport, archive_sport,
    get_coach_sports, set_coach_sports, get_athlete_sports, set_athlete_sports,
    get_athlete_login_info, set_athlete_login, update_user_password,
    list_assessments, get_assessment_by_id,
    log_audit,
)

bp = Blueprint("admin", __name__)


def _combine_name(form):
    """Join first / middle / last name fields into a single name string."""
    parts = [form.get("first_name", "").strip(),
             form.get("middle_name", "").strip(),
             form.get("last_name", "").strip()]
    return " ".join(p for p in parts if p)


def _split_name(full_name):
    """Split a stored full name into first / middle / last for the form."""
    parts = (full_name or "").split()
    if len(parts) == 0:
        return "", "", ""
    elif len(parts) == 1:
        return parts[0], "", ""
    elif len(parts) == 2:
        return parts[0], "", parts[1]
    else:
        return parts[0], " ".join(parts[1:-1]), parts[-1]


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
    all_sports = list_sports(is_archived=False)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        name = _combine_name(request.form)
        email = request.form.get("email", "").strip()
        specialty = request.form.get("specialty", "").strip()
        sport_ids = [int(x) for x in request.form.getlist("sport_ids") if x.isdigit()]

        gender = request.form.get("gender") or None
        dob = request.form.get("dob") or None
        phone = request.form.get("phone") or None
        address_line1 = request.form.get("address_line1") or None
        address_line2 = request.form.get("address_line2") or None
        city = request.form.get("city") or None
        state = request.form.get("state") or None
        postal_code = request.form.get("postal_code") or None
        education = request.form.get("education") or None
        certifications = request.form.get("certifications") or None
        additional_info = request.form.get("additional_info") or None
        achievements = request.form.get("achievements") or None

        missing = missing_coach_fields(request.form, sport_ids)
        if not username:
            missing.append("Username")
        if not password:
            missing.append("Password")
        if missing:
            flash(missing_fields_message(missing), "danger")
        elif get_user_by_username(username):
            flash("Username already exists.", "danger")
        else:
            coach_id = create_coach(username, password, name, email, specialty,
                                     created_by=session["user"]["id"],
                                     gender=gender, dob=dob, phone=phone,
                                     address_line1=address_line1, address_line2=address_line2,
                                     city=city, state=state, postal_code=postal_code,
                                     education=education, certifications=certifications,
                                     additional_info=additional_info, achievements=achievements)
            set_coach_sports(coach_id, sport_ids)
            log_audit(session["user"]["username"], "admin", "CREATE_COACH",
                      target_type="USER", details=f"username={username}")
            flash(f"Coach '{name}' created successfully.", "success")
            return redirect(url_for("admin.admin_coaches"))

    return render_template("admin_coach_form.html", coach=None, all_sports=all_sports, selected_sport_ids=[])


@bp.route("/admin/coaches/<username>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_coach_edit(username):
    user = get_user_by_username(username)
    if not user or user["role"] != "coach":
        flash("Coach not found.", "danger")
        return redirect(url_for("admin.admin_coaches"))

    coach = get_coach_by_user_id(user["id"])
    all_sports = list_sports(is_archived=False)
    selected_sport_ids = [s["id"] for s in get_coach_sports(coach["id"])] if coach else []

    if request.method == "POST":
        name = _combine_name(request.form)
        email = request.form.get("email", "").strip()
        specialty = request.form.get("specialty", "").strip()
        password = request.form.get("password", "")
        sport_ids = [int(x) for x in request.form.getlist("sport_ids") if x.isdigit()]

        gender = request.form.get("gender") or None
        dob = request.form.get("dob") or None
        phone = request.form.get("phone") or None
        address_line1 = request.form.get("address_line1") or None
        address_line2 = request.form.get("address_line2") or None
        city = request.form.get("city") or None
        state = request.form.get("state") or None
        postal_code = request.form.get("postal_code") or None
        education = request.form.get("education") or None
        certifications = request.form.get("certifications") or None
        additional_info = request.form.get("additional_info") or None
        achievements = request.form.get("achievements") or None

        missing = missing_coach_fields(request.form, sport_ids)
        if missing:
            flash(missing_fields_message(missing), "danger")
        else:
            update_coach(coach["id"], user["id"], name, email, specialty, password or None,
                         gender=gender, dob=dob, phone=phone,
                         address_line1=address_line1, address_line2=address_line2,
                         city=city, state=state, postal_code=postal_code,
                         education=education, certifications=certifications,
                         additional_info=additional_info, achievements=achievements)
            set_coach_sports(coach["id"], sport_ids)
            log_audit(session["user"]["username"], "admin", "UPDATE_COACH",
                      target_type="USER", target_id=user["id"])
            flash(f"Coach '{name}' updated successfully.", "success")
            return redirect(url_for("admin.admin_coaches"))

    first, middle, last = _split_name(user["name"])
    coach_data = {
        "username": username,
        "name": user["name"],
        "first_name": first,
        "middle_name": middle,
        "last_name": last,
        "email": user["email"],
        "specialty": coach["specialty"] if coach else "",
    }
    if coach:
        coach_data.update(coach)
    return render_template("admin_coach_form.html", coach=coach_data, all_sports=all_sports, selected_sport_ids=selected_sport_ids)


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
    status = "deactivated" if new_status else "activated"
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
    all_sports = list_sports(is_archived=False)
    coach_sports_map = {c["id"]: [s["id"] for s in get_coach_sports(c["id"])] for c in list_coaches(is_archived=False)}

    if request.method == "POST":
        first_name  = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip()
        last_name   = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        if phone and not phone.startswith("+91"):
            phone = "+91" + phone
        dob = request.form.get("dob", "").strip()
        coach_id = request.form.get("coach_id", "").strip()
        sport_ids = [int(x) for x in request.form.getlist("sport_ids") if x.isdigit()]
        sport_text = ", ".join(s["name"] for s in all_sports if s["id"] in sport_ids)

        height = request.form.get("height") or None
        weight = request.form.get("weight") or None
        parent_name = request.form.get("parent_name") or None
        father_name = request.form.get("father_name") or None
        mother_name = request.form.get("mother_name") or None
        address_line1 = request.form.get("address_line1") or None
        address_line2 = request.form.get("address_line2") or None
        city = request.form.get("city") or None
        state = request.form.get("state") or None
        postal_code = request.form.get("postal_code") or None
        gender = request.form.get("gender") or None
        blood_group = request.form.get("blood_group") or None
        emergency_contact_name = request.form.get("emergency_contact_name") or None
        emergency_contact_phone = request.form.get("emergency_contact_phone") or None
        sporting_experience_years = request.form.get("sporting_experience_years") or None
        sport_discipline = request.form.get("sport_discipline") or None
        level_of_participation = request.form.get("level_of_participation") or None
        previous_achievements = request.form.get("previous_achievements") or None
        nationality = request.form.get("nationality") or None
        id_proof_type = request.form.get("id_proof_type") or None
        id_proof_number = request.form.get("id_proof_number") or None
        school_name = request.form.get("school_name") or None
        school_grade = request.form.get("school_grade") or None
        admission_date = request.form.get("admission_date") or None
        medical_notes = request.form.get("medical_notes") or None

        login_username = request.form.get("login_username", "").strip()
        login_password = request.form.get("login_password", "")

        valid_coach_ids = {str(cid) for cid, _ in coach_choices}
        missing = missing_athlete_fields(request.form, sport_ids)
        if not coach_id:
            missing.append("Assigned coach")
        if missing:
            flash(missing_fields_message(missing), "danger")
        elif coach_id not in valid_coach_ids:
            flash("Selected coach is invalid.", "danger")
        elif not login_username or not login_password:
            flash("Username and password are required.", "danger")
        elif login_username and get_user_by_username(login_username):
            flash("That login username is already taken.", "danger")
        else:
            full_name = " ".join(p for p in [first_name, middle_name, last_name] if p)
            athlete_id = create_athlete(
                first_name, middle_name, last_name,
                email, phone, dob, sport_text, int(coach_id),
                created_by=session["user"]["id"],
                username=login_username or None, password=login_password or None,
                height=(float(height) if height else None), weight=(float(weight) if weight else None),
                parent_name=parent_name, father_name=father_name, mother_name=mother_name,
                address_line1=address_line1, address_line2=address_line2, city=city, state=state, postal_code=postal_code,
                gender=gender, blood_group=blood_group,
                emergency_contact_name=emergency_contact_name, emergency_contact_phone=emergency_contact_phone,
                sporting_experience_years=sporting_experience_years, sport_discipline=sport_discipline,
                level_of_participation=level_of_participation, previous_achievements=previous_achievements,
                nationality=nationality, id_proof_type=id_proof_type, id_proof_number=id_proof_number,
                school_name=school_name, school_grade=school_grade, admission_date=admission_date or None,
                medical_notes=medical_notes)
            set_athlete_sports(athlete_id, sport_ids)
            log_audit(session["user"]["username"], "admin", "CREATE_ATHLETE",
                      target_type="ATHLETE", target_id=athlete_id)
            flash(f"Athlete '{full_name}' created successfully.", "success")
            return redirect(url_for("admin.admin_athletes"))

    return render_template("admin_athlete_form.html", athlete=None, coaches=coach_choices,
                            all_sports=all_sports, coach_sports_map=coach_sports_map, selected_sport_ids=[],
                            login_info=None)


@bp.route("/admin/athletes/<int:athlete_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_athlete_edit(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("admin.admin_athletes"))

    coach_choices = [(c["id"], c["name"]) for c in list_coaches(is_archived=False)]
    all_sports = list_sports(is_archived=False)
    coach_sports_map = {c["id"]: [s["id"] for s in get_coach_sports(c["id"])] for c in list_coaches(is_archived=False)}
    selected_sport_ids = [s["id"] for s in get_athlete_sports(athlete_id)]
    login_info = get_athlete_login_info(athlete_id)

    if request.method == "POST":
        first_name  = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip()
        last_name   = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        if phone and not phone.startswith("+91"):
            phone = "+91" + phone
        dob = request.form.get("dob", "").strip()
        coach_id = request.form.get("coach_id", "").strip()
        sport_ids = [int(x) for x in request.form.getlist("sport_ids") if x.isdigit()]
        sport_text = ", ".join(s["name"] for s in all_sports if s["id"] in sport_ids)

        height = request.form.get("height") or None
        weight = request.form.get("weight") or None
        parent_name = request.form.get("parent_name") or None
        father_name = request.form.get("father_name") or None
        mother_name = request.form.get("mother_name") or None
        address_line1 = request.form.get("address_line1") or None
        address_line2 = request.form.get("address_line2") or None
        city = request.form.get("city") or None
        state = request.form.get("state") or None
        postal_code = request.form.get("postal_code") or None
        gender = request.form.get("gender") or None
        blood_group = request.form.get("blood_group") or None
        emergency_contact_name = request.form.get("emergency_contact_name") or None
        emergency_contact_phone = request.form.get("emergency_contact_phone") or None
        sporting_experience_years = request.form.get("sporting_experience_years") or None
        sport_discipline = request.form.get("sport_discipline") or None
        level_of_participation = request.form.get("level_of_participation") or None
        previous_achievements = request.form.get("previous_achievements") or None
        nationality = request.form.get("nationality") or None
        id_proof_type = request.form.get("id_proof_type") or None
        id_proof_number = request.form.get("id_proof_number") or None
        school_name = request.form.get("school_name") or None
        school_grade = request.form.get("school_grade") or None
        admission_date = request.form.get("admission_date") or None
        medical_notes = request.form.get("medical_notes") or None

        login_username = request.form.get("login_username", "").strip()
        login_password = request.form.get("login_password", "")

        valid_coach_ids = {str(cid) for cid, _ in coach_choices}
        missing = missing_athlete_fields(request.form, sport_ids)
        if not coach_id:
            missing.append("Assigned coach")
        if missing:
            flash(missing_fields_message(missing), "danger")
        elif coach_id not in valid_coach_ids:
            flash("Selected coach is invalid.", "danger")
        elif not login_info.get("user_id") and login_username and get_user_by_username(login_username):
            flash("That login username is already taken.", "danger")
        else:
            full_name = " ".join(p for p in [first_name, middle_name, last_name] if p)
            update_athlete(athlete_id, first_name, middle_name, last_name,
                           email, phone, dob, sport_text, int(coach_id),
                           height=(float(height) if height else None), weight=(float(weight) if weight else None),
                           parent_name=parent_name, father_name=father_name, mother_name=mother_name,
                           address_line1=address_line1, address_line2=address_line2, city=city, state=state, postal_code=postal_code,
                           gender=gender, blood_group=blood_group,
                           emergency_contact_name=emergency_contact_name, emergency_contact_phone=emergency_contact_phone,
                           sporting_experience_years=sporting_experience_years, sport_discipline=sport_discipline,
                           level_of_participation=level_of_participation, previous_achievements=previous_achievements,
                           nationality=nationality, id_proof_type=id_proof_type, id_proof_number=id_proof_number,
                           school_name=school_name, school_grade=school_grade, admission_date=admission_date or None,
                           medical_notes=medical_notes)
            set_athlete_sports(athlete_id, sport_ids)

            if login_info.get("user_id"):
                if login_password:
                    update_user_password(login_info["user_id"], login_password)
            elif login_username and login_password:
                set_athlete_login(athlete_id, full_name, email, login_username, login_password,
                                   created_by=session["user"]["id"])

            log_audit(session["user"]["username"], "admin", "UPDATE_ATHLETE",
                      target_type="ATHLETE", target_id=athlete_id)
            flash(f"Athlete '{full_name}' updated successfully.", "success")
            return redirect(url_for("admin.admin_athletes"))

    if athlete.get("phone") and athlete["phone"].startswith("+91"):
        athlete["phone"] = athlete["phone"][3:]
    return render_template("admin_athlete_form.html", athlete=athlete, coaches=coach_choices,
                            all_sports=all_sports, coach_sports_map=coach_sports_map,
                            selected_sport_ids=selected_sport_ids, login_info=login_info)


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
    status = "deactivated" if new_status else "activated"
    flash(f"Athlete '{athlete['name']}' has been {status}.", "success")
    return redirect(url_for("admin.admin_athletes"))


# --------------------------------------------------------------------
# Sports Master
# --------------------------------------------------------------------

@bp.route("/admin/sports")
@login_required
@role_required("admin")
def admin_sports():
    return render_template("admin_sports.html", sports=list_sports())


@bp.route("/admin/sports/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_sport_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Sport name is required.", "danger")
        elif get_sport_by_name(name):
            flash("This sport already exists.", "danger")
        else:
            create_sport(name)
            log_audit(session["user"]["username"], "admin", "CREATE_SPORT",
                      target_type="SPORT", details=f"name={name}")
            flash(f"Sport '{name}' created successfully.", "success")
            return redirect(url_for("admin.admin_sports"))

    return render_template("admin_sport_form.html", sport=None)


@bp.route("/admin/sports/<int:sport_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_sport_edit(sport_id):
    sport = get_sport_by_id(sport_id)
    if not sport:
        flash("Sport not found.", "danger")
        return redirect(url_for("admin.admin_sports"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        existing = get_sport_by_name(name)
        if not name:
            flash("Sport name is required.", "danger")
        elif existing and existing["id"] != sport_id:
            flash("Another sport already has this name.", "danger")
        else:
            update_sport(sport_id, name)
            log_audit(session["user"]["username"], "admin", "UPDATE_SPORT",
                      target_type="SPORT", target_id=sport_id)
            flash(f"Sport '{name}' updated successfully.", "success")
            return redirect(url_for("admin.admin_sports"))

    return render_template("admin_sport_form.html", sport=sport)


@bp.route("/admin/sports/<int:sport_id>/archive", methods=["POST"])
@login_required
@role_required("admin")
def admin_sport_archive(sport_id):
    sport = get_sport_by_id(sport_id)
    if not sport:
        flash("Sport not found.", "danger")
        return redirect(url_for("admin.admin_sports"))

    new_status = not sport["is_archived"]
    archive_sport(sport_id, new_status)
    log_audit(session["user"]["username"], "admin",
              "ARCHIVE_SPORT" if new_status else "UNARCHIVE_SPORT",
              target_type="SPORT", target_id=sport_id)
    status = "deactivated" if new_status else "activated"
    flash(f"Sport '{sport['name']}' has been {status}.", "success")
    return redirect(url_for("admin.admin_sports"))


# --------------------------------------------------------------------
# Assessment View-Only Access for Admin
# --------------------------------------------------------------------

@bp.route("/admin/athletes/<int:athlete_id>/assessments")
@login_required
@role_required("admin")
def admin_athlete_assessments(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("admin.admin_athletes"))
    assessments = list_assessments(athlete_id=athlete_id, is_archived=False)
    return render_template("coach_assessment_history.html", athlete=athlete, assessments=assessments, read_only=True)


@bp.route("/admin/assessments/<int:id>")
@login_required
@role_required("admin")
def admin_assessment_view(id):
    assessment = get_assessment_by_id(id)
    if not assessment:
        flash("Assessment not found.", "danger")
        return redirect(url_for("admin.admin_athletes"))
    athlete = get_athlete_by_id(assessment["athlete_id"])
    return render_template("coach_assessment_view.html", athlete=athlete, assessment=assessment, read_only=True)

