from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify

from common.decorators import login_required, role_required
from common.portall_client import upload_document, get_task_status, PortallError
from common.models import (
    list_athletes, get_athlete_by_id, create_athlete, update_athlete,
    archive_athlete, log_audit,
    ASSESSMENT_FIELDS, compute_age_and_focus, compute_attendance_pct,
    get_assessment_by_id, list_assessments, create_assessment, update_assessment,
    archive_assessment, get_coach_analytics, get_athlete_analytics,
    get_squad_performance_dashboard, get_athlete_recommendations,
    get_coach_sports, get_athlete_sports, set_athlete_sports,
    get_athlete_login_info, set_athlete_login, get_user_by_username, update_user_password,
    send_assessment_email,
)

bp = Blueprint("coach", __name__)


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


def _coach_id():
    return session["user"]["coach_id"]


def _my_athletes():
    return list_athletes(coach_id=_coach_id())


@bp.route("/coach")
@login_required
@role_required("coach")
def coach_panel():
    return render_template("coach.html", user=session["user"], athletes=_my_athletes())


@bp.route("/coach/athletes")
@login_required
@role_required("coach")
def coach_athletes():
    athletes = _my_athletes()
    q = (request.args.get("q") or "").strip().lower()
    status_filter = (request.args.get("status") or "all").lower()
    sport_filter = (request.args.get("sport") or "").strip()
    sort = (request.args.get("sort") or "id").lower()
    direction = (request.args.get("dir") or "asc").lower()

    if direction not in {"asc", "desc"}:
        direction = "asc"

    valid_sort = {"id": "id", "name": "name", "email": "email",
                  "phone": "phone", "sport": "sport", "status": "is_archived"}
    sort = valid_sort.get(sort, "id")

    def matches_filters(athlete):
        if q:
            haystack = " ".join(
                str(athlete.get(field) or "") for field in ("id", "name", "email", "phone", "sport")
            ).lower()
            if q not in haystack:
                return False

        if status_filter == "active" and athlete.get("is_archived"):
            return False
        if status_filter == "inactive" and not athlete.get("is_archived"):
            return False

        if sport_filter and (athlete.get("sport") or "").lower() != sport_filter.lower():
            return False

        return True

    filtered_athletes = [athlete for athlete in athletes if matches_filters(athlete)]

    def sort_value(athlete):
        if sort == "status":
            return bool(athlete.get("is_archived"))
        value = athlete.get(sort)
        if sort == "id":
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
        if value is None:
            return ""
        return str(value).lower()

    filtered_athletes.sort(key=sort_value, reverse=(direction == "desc"))

    sports = sorted({(athlete.get("sport") or "").strip() for athlete in athletes if athlete.get("sport")}, key=str.lower)

    return render_template(
        "coach_athletes.html",
        athletes=filtered_athletes,
        filter_query=q,
        filter_status=status_filter,
        filter_sport=sport_filter,
        sort=sort,
        dir=direction,
        sports=sports,
    )


@bp.route("/coach/athletes/create", methods=["GET", "POST"])
@login_required
@role_required("coach")
def coach_athlete_create():
    # A coach can only assign athletes to sports THEY have been assigned to
    # (see Sports Master, managed by admin/superadmin).
    my_sports = get_coach_sports(_coach_id())

    if request.method == "POST":
        first_name  = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip()
        last_name   = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        if phone and not phone.startswith("+91"):
            phone = "+91" + phone
        dob = request.form.get("dob", "").strip()
        my_sport_ids = {s["id"] for s in my_sports}
        sport_ids = [int(x) for x in request.form.getlist("sport_ids")
                     if x.isdigit() and int(x) in my_sport_ids]
        sport_text = ", ".join(s["name"] for s in my_sports if s["id"] in sport_ids)
        login_username = request.form.get("login_username", "").strip()
        login_password = request.form.get("login_password", "")

        if not first_name or not last_name:
            flash("First name and last name are required.", "danger")
        elif not login_username or not login_password:
            flash("Username and password are required.", "danger")
        elif login_username and get_user_by_username(login_username):
            flash("That login username is already taken.", "danger")
        else:
            height = request.form.get('height') or None
            weight = request.form.get('weight') or None
            parent_name = request.form.get('parent_name') or None
            father_name = request.form.get('father_name') or None
            mother_name = request.form.get('mother_name') or None
            address_line1 = request.form.get('address_line1') or None
            address_line2 = request.form.get('address_line2') or None
            city = request.form.get('city') or None
            state = request.form.get('state') or None
            postal_code = request.form.get('postal_code') or None
            gender = request.form.get('gender') or None
            blood_group = request.form.get('blood_group') or None
            emergency_contact_name = request.form.get('emergency_contact_name') or None
            emergency_contact_phone = request.form.get('emergency_contact_phone') or None
            sporting_experience_years = request.form.get('sporting_experience_years') or None
            sport_discipline = request.form.get('sport_discipline') or None
            level_of_participation = request.form.get('level_of_participation') or None
            previous_achievements = request.form.get('previous_achievements') or None
            nationality = request.form.get('nationality') or None
            id_proof_type = request.form.get('id_proof_type') or None
            id_proof_number = request.form.get('id_proof_number') or None
            school_name = request.form.get('school_name') or None
            school_grade = request.form.get('school_grade') or None
            admission_date = request.form.get('admission_date') or None
            medical_notes = request.form.get('medical_notes') or None

            physical_params = {}
            if height:
                try:
                    physical_params['height'] = float(height)
                except Exception:
                    pass
            if weight:
                try:
                    physical_params['weight'] = float(weight)
                except Exception:
                    pass

            athlete_id = create_athlete(
                first_name, middle_name, last_name,
                email, phone, dob, sport_text,
                _coach_id(), created_by=session["user"]["id"],
                username=login_username or None,
                password=login_password or None,
                height=(float(height) if height else None),
                weight=(float(weight) if weight else None),
                parent_name=parent_name, father_name=father_name, mother_name=mother_name,
                address_line1=address_line1, address_line2=address_line2, city=city,
                state=state, postal_code=postal_code,
                physical_params=physical_params or None,
                gender=gender, blood_group=blood_group,
                emergency_contact_name=emergency_contact_name, emergency_contact_phone=emergency_contact_phone,
                sporting_experience_years=sporting_experience_years, sport_discipline=sport_discipline,
                level_of_participation=level_of_participation, previous_achievements=previous_achievements,
                nationality=nationality, id_proof_type=id_proof_type, id_proof_number=id_proof_number,
                school_name=school_name, school_grade=school_grade, admission_date=admission_date or None,
                medical_notes=medical_notes,
            )
            set_athlete_sports(athlete_id, sport_ids)
            log_audit(session["user"]["username"], "coach", "CREATE_ATHLETE",
                      target_type="ATHLETE", target_id=athlete_id)
            full_name = " ".join(p for p in [first_name, middle_name, last_name] if p)
            flash(f"Athlete '{full_name}' created successfully.", "success")
            return redirect(url_for("coach.coach_athletes"))

    return render_template("coach_athlete_form.html", athlete=None, my_sports=my_sports,
                           selected_sport_ids=[], login_info=None)


@bp.route("/coach/athletes/<int:athlete_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("coach")
def coach_athlete_edit(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete or athlete["coach_id"] != _coach_id():
        flash("Athlete not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    my_sports = get_coach_sports(_coach_id())
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
        my_sport_ids = {s["id"] for s in my_sports}
        sport_ids = [int(x) for x in request.form.getlist("sport_ids")
                     if x.isdigit() and int(x) in my_sport_ids]
        sport_text = ", ".join(s["name"] for s in my_sports if s["id"] in sport_ids)

        height = request.form.get('height') or None
        weight = request.form.get('weight') or None
        parent_name = request.form.get('parent_name') or None
        father_name = request.form.get('father_name') or None
        mother_name = request.form.get('mother_name') or None
        address_line1 = request.form.get('address_line1') or None
        address_line2 = request.form.get('address_line2') or None
        city = request.form.get('city') or None
        state = request.form.get('state') or None
        postal_code = request.form.get('postal_code') or None
        gender = request.form.get('gender') or None
        blood_group = request.form.get('blood_group') or None
        emergency_contact_name = request.form.get('emergency_contact_name') or None
        emergency_contact_phone = request.form.get('emergency_contact_phone') or None
        sporting_experience_years = request.form.get('sporting_experience_years') or None
        sport_discipline = request.form.get('sport_discipline') or None
        level_of_participation = request.form.get('level_of_participation') or None
        previous_achievements = request.form.get('previous_achievements') or None
        nationality = request.form.get('nationality') or None
        id_proof_type = request.form.get('id_proof_type') or None
        id_proof_number = request.form.get('id_proof_number') or None
        school_name = request.form.get('school_name') or None
        school_grade = request.form.get('school_grade') or None
        admission_date = request.form.get('admission_date') or None
        medical_notes = request.form.get('medical_notes') or None

        login_password = request.form.get("login_password", "")
        login_username = request.form.get("login_username", "").strip()

        if not first_name or not last_name:
            flash("First name and last name are required.", "danger")
        elif not login_info.get("user_id") and login_username and get_user_by_username(login_username):
            flash("That login username is already taken.", "danger")
        else:
            update_athlete(athlete_id, first_name, middle_name, last_name,
                           email, phone, dob, sport_text, _coach_id(),
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
                full_name = " ".join(p for p in [first_name, middle_name, last_name] if p)
                set_athlete_login(athlete_id, full_name, email, login_username, login_password,
                                   created_by=session["user"]["id"])

            log_audit(session["user"]["username"], "coach", "UPDATE_ATHLETE",
                      target_type="ATHLETE", target_id=athlete_id)
            full_name = " ".join(p for p in [first_name, middle_name, last_name] if p)
            flash(f"Athlete '{full_name}' updated successfully.", "success")
            return redirect(url_for("coach.coach_athletes"))

    if athlete.get("phone") and athlete["phone"].startswith("+91"):
        athlete["phone"] = athlete["phone"][3:]
    return render_template("coach_athlete_form.html", athlete=athlete, my_sports=my_sports,
                            selected_sport_ids=selected_sport_ids, login_info=login_info)


@bp.route("/coach/athletes/<int:athlete_id>/archive", methods=["POST"])
@login_required
@role_required("coach")
def coach_athlete_archive(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete or athlete["coach_id"] != _coach_id():
        flash("Athlete not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    new_status = not athlete["is_archived"]
    archive_athlete(athlete_id, new_status)
    log_audit(session["user"]["username"], "coach",
              "ARCHIVE_ATHLETE" if new_status else "UNARCHIVE_ATHLETE",
              target_type="ATHLETE", target_id=athlete_id)
    status = "deactivated" if new_status else "activated"
    flash(f"Athlete '{athlete['name']}' has been {status}.", "success")
    return redirect(url_for("coach.coach_athletes"))


# ---------------------------------------------------------------------------
# Athlete Assessments
# ---------------------------------------------------------------------------

def _owned_athlete_or_404(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete or athlete["coach_id"] != _coach_id():
        return None
    return athlete


def _owned_assessment_or_404(assessment_id):
    assessment = get_assessment_by_id(assessment_id)
    if not assessment or assessment["coach_id"] != _coach_id():
        return None
    return assessment


def _collect_assessment_form(request_form) -> dict:
    """Pulls all ASSESSMENT_FIELDS out of request.form into a plain dict."""
    return {field: request_form.get(field, "").strip() for field in ASSESSMENT_FIELDS}


def _validate_assessment(data: dict, is_submit: bool) -> list[str]:
    """Only enforced on Submit — Draft can be saved partially at any time."""
    errors = []
    if not is_submit:
        return errors

    required_ratings = [
        "speed_rating", "agility_rating", "balance_rating", "coordination_rating",
        "strength_rating", "endurance_rating", "technique_rating",
        "control_accuracy_rating", "footwork_rating", "game_awareness_rating",
        "decision_making_rating", "follow_instructions_rating", "discipline_rating",
        "effort_rating", "coachability_rating", "confidence_rating", "team_behaviour_rating",
    ]
    for field in required_ratings:
        if not data.get(field):
            errors.append(f"'{field.replace('_', ' ').title()}' is required to submit.")

    if not data.get("talent_category"):
        errors.append("Talent Identification Marker is required.")
    if not data.get("talent_justification") or len(data["talent_justification"]) < 20:
        errors.append("Justification must be at least 20 characters.")
    if not data.get("strength_1"):
        errors.append("At least one Key Strength is required.")
    if not data.get("improvement_1"):
        errors.append("At least one Key Area for Improvement is required.")
    if not data.get("overall_progress"):
        errors.append("Overall Progress rating is required.")

    return errors


@bp.route("/coach/athletes/<int:athlete_id>/assessments")
@login_required
@role_required("coach")
def coach_assessment_history(athlete_id):
    athlete = _owned_athlete_or_404(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    assessments = list_assessments(athlete_id=athlete_id, coach_id=_coach_id())
    return render_template("coach_assessment_history.html", athlete=athlete, assessments=assessments)


@bp.route("/coach/athletes/<int:athlete_id>/assessment/new", methods=["GET", "POST"])
@login_required
@role_required("coach")
def coach_assessment_new(athlete_id):
    athlete = _owned_athlete_or_404(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    if request.method == "POST":
        action = request.form.get("action", "draft")  # 'draft' or 'submit'
        data = _collect_assessment_form(request.form)

        age, focus = compute_age_and_focus(athlete.get("dob"))
        data["calculated_age"] = age
        data["age_group_focus"] = focus
        data["attendance_pct"] = compute_attendance_pct(
            data.get("sessions_planned"), data.get("sessions_attended")
        )

        status = "Submitted" if action == "submit" else "Draft"
        errors = _validate_assessment(data, is_submit=(action == "submit"))
        if errors:
            for e in errors:
                flash(e, "danger")
            data["assessment_date"] = request.form.get("assessment_date")
            return render_template("coach_assessment_form.html", athlete=athlete,
                                    assessment=data, is_new=True, today=date.today().isoformat())

        assessment_id = create_assessment(
            athlete_id, _coach_id(), request.form.get("assessment_date") or date.today().isoformat(),
            status, data, created_by=session["user"]["id"],
        )
        log_audit(session["user"]["username"], "coach",
                  "SUBMIT_ASSESSMENT" if status == "Submitted" else "DRAFT_ASSESSMENT",
                  target_type="ASSESSMENT", target_id=assessment_id)
        flash(f"Assessment {'submitted' if status == 'Submitted' else 'saved as draft'} for {athlete['name']}.",
              "success")
        return redirect(url_for("coach.coach_athletes"))

    age, focus = compute_age_and_focus(athlete.get("dob"))
    blank = {f: "" for f in ASSESSMENT_FIELDS}
    blank["calculated_age"] = age
    blank["age_group_focus"] = focus
    return render_template("coach_assessment_form.html", athlete=athlete, assessment=blank,
                            is_new=True, today=date.today().isoformat())


@bp.route("/coach/assessments/<int:assessment_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("coach")
def coach_assessment_edit(assessment_id):
    assessment = _owned_assessment_or_404(assessment_id)
    if not assessment:
        flash("Assessment not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    athlete = get_athlete_by_id(assessment["athlete_id"])

    if request.method == "POST":
        action = request.form.get("action", "draft")
        data = _collect_assessment_form(request.form)

        age, focus = compute_age_and_focus(athlete.get("dob"))
        data["calculated_age"] = age
        data["age_group_focus"] = focus
        data["attendance_pct"] = compute_attendance_pct(
            data.get("sessions_planned"), data.get("sessions_attended")
        )

        status = "Submitted" if action == "submit" else "Draft"
        errors = _validate_assessment(data, is_submit=(action == "submit"))
        if errors:
            for e in errors:
                flash(e, "danger")
            data["assessment_date"] = request.form.get("assessment_date")
            return render_template("coach_assessment_form.html", athlete=athlete,
                                    assessment=data, is_new=False, assessment_id=assessment_id,
                                    today=date.today().isoformat())

        update_assessment(assessment_id, status, data)
        log_audit(session["user"]["username"], "coach",
                  "SUBMIT_ASSESSMENT" if status == "Submitted" else "UPDATE_ASSESSMENT_DRAFT",
                  target_type="ASSESSMENT", target_id=assessment_id)
        flash(f"Assessment {'submitted' if status == 'Submitted' else 'updated'} for {athlete['name']}.",
              "success")
        return redirect(url_for("coach.coach_assessment_history", athlete_id=athlete["id"]))

    return render_template("coach_assessment_form.html", athlete=athlete, assessment=assessment,
                            is_new=False, assessment_id=assessment_id, today=date.today().isoformat())


@bp.route("/coach/assessments/<int:assessment_id>/view")
@login_required
@role_required("coach")
def coach_assessment_view(assessment_id):
    assessment = _owned_assessment_or_404(assessment_id)
    if not assessment:
        flash("Assessment not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    athlete = get_athlete_by_id(assessment["athlete_id"])
    return render_template("coach_assessment_view.html", athlete=athlete, assessment=assessment,
                            assessment_id=assessment_id)


@bp.route("/coach/assessments/<int:assessment_id>/send-email", methods=["POST"])
@login_required
def coach_assessment_send_email(assessment_id):
    recipient_email = request.form.get("recipient_email", "").strip()
    if not recipient_email and request.is_json and request.json:
        recipient_email = request.json.get("recipient_email", "").strip()

    result = send_assessment_email(assessment_id, recipient_email or None)

    if request.is_json:
        return jsonify(result)

    if result.get("success"):
        flash(result.get("message", "Assessment email processed."), "success")
    else:
        flash(result.get("message", "Failed to send email."), "danger")

    return redirect(request.referrer or url_for("coach.coach_assessment_view", assessment_id=assessment_id))



@bp.route("/coach/assessments/<int:assessment_id>/archive", methods=["POST"])
@login_required
@role_required("coach")
def coach_assessment_archive(assessment_id):
    assessment = _owned_assessment_or_404(assessment_id)
    if not assessment:
        flash("Assessment not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    new_status = not assessment["is_archived"]
    archive_assessment(assessment_id, new_status)
    log_audit(session["user"]["username"], "coach",
              "ARCHIVE_ASSESSMENT" if new_status else "UNARCHIVE_ASSESSMENT",
              target_type="ASSESSMENT", target_id=assessment_id)
    flash("Assessment archived." if new_status else "Assessment unarchived.", "success")
    return redirect(url_for("coach.coach_assessment_history", athlete_id=assessment["athlete_id"]))


@bp.route("/coach/athletes/<int:athlete_id>/assessment/import-upload", methods=["POST"])
@login_required
@role_required("coach")
def coach_assessment_import_upload(athlete_id):
    """Uploads a scanned form / PDF / Excel sheet to the Portall extraction
    service on behalf of the coach. Returns a task_id the browser polls via
    coach_assessment_import_status() -- no assessment data is written here,
    this only kicks off extraction."""
    athlete = _owned_athlete_or_404(athlete_id)
    if not athlete:
        return jsonify(error="Athlete not found."), 404

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify(error="No file selected."), 400

    try:
        result = upload_document(file)
    except PortallError as e:
        return jsonify(error=str(e)), 502

    log_audit(session["user"]["username"], "coach", "IMPORT_ASSESSMENT_UPLOAD",
              target_type="ATHLETE", target_id=athlete_id,
              details=f"task_id={result.get('task_id')} filename={file.filename}")
    return jsonify(task_id=result.get("task_id"), status=result.get("status"))


@bp.route("/coach/assessment/import-status/<task_id>")
@login_required
@role_required("coach")
def coach_assessment_import_status(task_id):
    """Proxies the Portall status/result lookup so the API key never reaches
    the browser. Returns the raw {success, status, data, ...} response."""
    try:
        result = get_task_status(task_id)
    except PortallError as e:
        return jsonify(error=str(e)), 502
    return jsonify(result)


# ---------------------------------------------------------------------------
# Performance Analytics Dashboards
# ---------------------------------------------------------------------------

@bp.route("/coach/analytics")
@login_required
@role_required("coach")
def coach_analytics():
    dashboard = get_squad_performance_dashboard(_coach_id())
    # ?athlete_id=<id> lets other pages (e.g. the athlete list) deep-link
    # straight to a specific athlete inside this unified dashboard.
    focus_athlete_id = request.args.get("athlete_id", type=int)
    return render_template("coach_analytics.html", dashboard=dashboard, focus_athlete_id=focus_athlete_id)


@bp.route("/coach/athletes/<int:athlete_id>/analytics")
@login_required
@role_required("coach")
def coach_athlete_analytics(athlete_id):
    # Deprecated: the standalone per-athlete dashboard has been merged into
    # the squad analytics page, which can focus a single athlete via
    # ?athlete_id=. Kept as a redirect so old links/bookmarks still work.
    athlete = _owned_athlete_or_404(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    return redirect(url_for("coach.coach_analytics", athlete_id=athlete_id))


@bp.route("/coach/athletes/<int:athlete_id>/recommendations")
@login_required
@role_required("coach")
def coach_athlete_recommendations(athlete_id):
    athlete = _owned_athlete_or_404(athlete_id)
    if not athlete:
        return jsonify(error="Athlete not found"), 404

    recs = get_athlete_recommendations(athlete_id, _coach_id())
    return jsonify(recs=recs)








