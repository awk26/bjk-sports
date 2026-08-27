from flask import Blueprint, render_template, session, redirect, url_for, flash

from common.decorators import login_required, role_required
from common.models import (
    get_athlete_by_id, get_coach_by_id, get_athlete_analytics,
    get_athlete_sports, list_assessments,
)

bp = Blueprint("athlete", __name__, url_prefix="/athlete")


def _athlete_id():
    return session["user"]["athlete_id"]


def _my_athlete():
    return get_athlete_by_id(_athlete_id())


@bp.route("/")
@login_required
@role_required("athlete")
def athlete_dashboard():
    athlete = _my_athlete()
    if not athlete:
        flash("Your athlete profile could not be found. Please contact your coach.", "danger")
        return redirect(url_for("auth.logout"))

    analytics = get_athlete_analytics(athlete["id"], athlete["coach_id"])
    return render_template("athlete_dashboard.html", athlete=athlete, analytics=analytics)


@bp.route("/profile")
@login_required
@role_required("athlete")
def athlete_profile():
    athlete = _my_athlete()
    if not athlete:
        flash("Your athlete profile could not be found. Please contact your coach.", "danger")
        return redirect(url_for("auth.logout"))

    coach = get_coach_by_id(athlete["coach_id"])
    sports = get_athlete_sports(athlete["id"])
    assessment_count = len(list_assessments(athlete_id=athlete["id"], is_archived=False))

    return render_template("athlete_profile.html", athlete=athlete, coach=coach,
                            sports=sports, assessment_count=assessment_count)
