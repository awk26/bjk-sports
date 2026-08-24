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
)

bp = Blueprint("coach", __name__)


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
    return render_template("coach_athletes.html", athletes=_my_athletes())


@bp.route("/coach/athletes/create", methods=["GET", "POST"])
@login_required
@role_required("coach")
def coach_athlete_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        dob = request.form.get("dob", "").strip()
        sport = request.form.get("sport", "").strip()

        if not name:
            flash("Athlete name is required.", "danger")
        else:
            athlete_id = create_athlete(name, email, phone, dob, sport,
                                         _coach_id(), created_by=session["user"]["id"])
            log_audit(session["user"]["username"], "coach", "CREATE_ATHLETE",
                      target_type="ATHLETE", target_id=athlete_id)
            flash(f"Athlete '{name}' created successfully.", "success")
            return redirect(url_for("coach.coach_athletes"))

    return render_template("coach_athlete_form.html", athlete=None)


@bp.route("/coach/athletes/<int:athlete_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("coach")
def coach_athlete_edit(athlete_id):
    athlete = get_athlete_by_id(athlete_id)
    if not athlete or athlete["coach_id"] != _coach_id():
        flash("Athlete not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        dob = request.form.get("dob", "").strip()
        sport = request.form.get("sport", "").strip()

        if not name:
            flash("Athlete name is required.", "danger")
        else:
            update_athlete(athlete_id, name, email, phone, dob, sport, _coach_id())
            log_audit(session["user"]["username"], "coach", "UPDATE_ATHLETE",
                      target_type="ATHLETE", target_id=athlete_id)
            flash(f"Athlete '{name}' updated successfully.", "success")
            return redirect(url_for("coach.coach_athletes"))

    return render_template("coach_athlete_form.html", athlete=athlete)


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
    status = "archived" if new_status else "unarchived"
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
    return render_template("coach_analytics.html", dashboard=dashboard)


@bp.route("/coach/athletes/<int:athlete_id>/analytics")
@login_required
@role_required("coach")
def coach_athlete_analytics(athlete_id):
    athlete = _owned_athlete_or_404(athlete_id)
    if not athlete:
        flash("Athlete not found.", "danger")
        return redirect(url_for("coach.coach_athletes"))

    analytics = get_athlete_analytics(athlete_id, _coach_id())
    return render_template("coach_athlete_analytics.html", athlete=athlete, analytics=analytics)


@bp.route("/coach/athletes/<int:athlete_id>/recommendations")
@login_required
@role_required("coach")
def coach_athlete_recommendations(athlete_id):
    athlete = _owned_athlete_or_404(athlete_id)
    if not athlete:
        return jsonify(error="Athlete not found"), 404

    recs = get_athlete_recommendations(athlete_id, _coach_id())
    return jsonify(recs=recs)
