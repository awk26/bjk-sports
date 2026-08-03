import os
import secrets
from datetime import datetime, timedelta, date

from werkzeug.security import generate_password_hash, check_password_hash

from .config import Config
from .database import Database
from .gemini_recommendations import generate_coaching_recommendations

db = Database()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def verify_superadmin(username: str, password: str) -> bool:
    """Super admin is hardcoded and never stored in the users table."""
    return username == Config.SUPERADMIN_USERNAME and password == Config.SUPERADMIN_PASSWORD


def verify_user(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)
    if not user:
        return None
    if user["is_archived"]:
        return None
    if check_password_hash(user["password_hash"], password):
        return user
    return None


# ---------------------------------------------------------------------------
# Users (admin / coach accounts)
# ---------------------------------------------------------------------------

def get_user_by_id(user_id: int) -> dict | None:
    rows = db.call_proc("sp_user_get_by_id", (user_id,))["rows"]
    return rows[0] if rows else None


def get_user_by_username(username: str) -> dict | None:
    rows = db.call_proc("sp_user_get_by_username", (username,))["rows"]
    return rows[0] if rows else None


def list_users(role: str | None = None, is_archived: bool | None = None) -> list[dict]:
    return db.call_proc("sp_user_list", (role, is_archived))["rows"]


def create_user(username, password, role, name, email, created_by=None) -> int:
    password_hash = generate_password_hash(password)
    result = db.call_proc(
        "sp_user_create",
        (username, password_hash, role, name, email, created_by, None),
    )
    return result["out_params"]["p6"]


def update_user(user_id: int, name: str, email: str):
    db.call_proc("sp_user_update", (user_id, name, email))


def update_user_password(user_id: int, password: str):
    db.call_proc("sp_user_update_password", (user_id, generate_password_hash(password)))


def archive_user(user_id: int, is_archived: bool):
    db.call_proc("sp_user_archive", (user_id, is_archived))


def delete_user(user_id: int):
    db.call_proc("sp_user_delete", (user_id,))


# ---------------------------------------------------------------------------
# Coaches
# ---------------------------------------------------------------------------

def get_coach_by_id(coach_id: int) -> dict | None:
    rows = db.call_proc("sp_coach_get_by_id", (coach_id,))["rows"]
    return rows[0] if rows else None


def get_coach_by_user_id(user_id: int) -> dict | None:
    rows = db.call_proc("sp_coach_get_by_user_id", (user_id,))["rows"]
    return rows[0] if rows else None


def list_coaches(is_archived: bool | None = None) -> list[dict]:
    return db.call_proc("sp_coach_list", (is_archived,))["rows"]


def create_coach(username, password, name, email, specialty, created_by=None) -> int:
    """Creates the underlying user (role='coach') then the coach detail row."""
    user_id = create_user(username, password, "coach", name, email, created_by)
    result = db.call_proc("sp_coach_create", (user_id, specialty, None))
    return result["out_params"]["p2"]


def update_coach(coach_id: int, user_id: int, name: str, email: str, specialty: str, password: str | None = None):
    update_user(user_id, name, email)
    if password:
        update_user_password(user_id, password)
    db.call_proc("sp_coach_update", (coach_id, specialty))


def archive_coach(coach_id: int, is_archived: bool):
    """Archives the coach row and cascades the flag onto the linked user (login)."""
    db.call_proc("sp_coach_archive", (coach_id, is_archived))


# ---------------------------------------------------------------------------
# Athletes
# ---------------------------------------------------------------------------

def get_athlete_by_id(athlete_id: int) -> dict | None:
    rows = db.call_proc("sp_athlete_get_by_id", (athlete_id,))["rows"]
    return rows[0] if rows else None


def list_athletes(coach_id=None, is_archived=None, sport=None, search=None) -> list[dict]:
    return db.call_proc("sp_athlete_list", (coach_id, is_archived, sport, search))["rows"]


def _next_athlete_code() -> str:
    rows = db.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM athletes")
    next_id = rows[0]["next_id"] if rows else 1
    return f"ATH-{next_id:03d}"


def create_athlete(name, email, phone, dob, sport, coach_id, created_by=None) -> int:
    code = _next_athlete_code()
    result = db.call_proc(
        "sp_athlete_create",
        (code, name, email or None, phone or None, dob or None, sport or None,
         coach_id, created_by, None),
    )
    return result["out_params"]["p8"]


def update_athlete(athlete_id, name, email, phone, dob, sport, coach_id):
    db.call_proc(
        "sp_athlete_update",
        (athlete_id, name, email or None, phone or None, dob or None, sport or None, coach_id),
    )


def archive_athlete(athlete_id: int, is_archived: bool):
    db.call_proc("sp_athlete_archive", (athlete_id, is_archived))


def delete_athlete(athlete_id: int):
    db.call_proc("sp_athlete_delete", (athlete_id,))


# ---------------------------------------------------------------------------
# Password reset tokens
# ---------------------------------------------------------------------------

def create_reset_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)
    db.call_proc("sp_reset_token_create", (token, user_id, expires_at))
    return token


def get_reset_token(token: str) -> dict | None:
    """Peek at a token without consuming it (safe to call on GET)."""
    rows = db.call_proc("sp_reset_token_get", (token,))["rows"]
    return rows[0] if rows else None


def mark_reset_token_used(token: str):
    db.call_proc("sp_reset_token_mark_used", (token,))


def purge_expired_reset_tokens():
    db.call_proc("sp_reset_token_delete_expired", ())


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def log_audit(actor_username, actor_role, action, target_type=None, target_id=None, details=None):
    db.call_proc(
        "sp_audit_log_insert",
        (actor_username, actor_role, action, target_type, target_id, details),
    )


def list_audit_log(target_type=None, target_id=None, limit=50):
    return db.call_proc("sp_audit_log_list", (target_type, target_id, limit))["rows"]


# ---------------------------------------------------------------------------
# Athlete Assessments
# ---------------------------------------------------------------------------
# ASSESSMENT_FIELDS is the single source of truth for field order. It maps
# 1:1 with the IN parameters of sp_assessment_create / sp_assessment_update
# in common/assessment_schema.sql — do not reorder without updating both.
ASSESSMENT_FIELDS = [
    "calculated_age", "age_group_focus", "level",
    "sessions_planned", "sessions_attended", "attendance_pct", "attendance_remarks",
    "speed_rating", "speed_remarks",
    "agility_rating", "agility_remarks",
    "balance_rating", "balance_remarks",
    "coordination_rating", "coordination_remarks",
    "strength_rating", "strength_remarks",
    "endurance_rating", "endurance_remarks",
    "technique_rating", "technique_remarks",
    "control_accuracy_rating", "control_accuracy_remarks",
    "footwork_rating", "footwork_remarks",
    "game_awareness_rating", "game_awareness_remarks",
    "decision_making_rating", "decision_making_remarks",
    "follow_instructions_rating", "follow_instructions_remarks",
    "discipline_rating", "discipline_remarks",
    "effort_rating", "effort_remarks",
    "coachability_rating", "coachability_remarks",
    "confidence_rating", "confidence_remarks",
    "team_behaviour_rating", "team_behaviour_remarks",
    "talent_category", "talent_justification",
    "strength_1", "strength_2", "strength_3",
    "improvement_1", "improvement_2", "improvement_3",
    "idp_technical_action", "idp_technical_responsibility",
    "idp_physical_action", "idp_physical_responsibility",
    "idp_behavioral_action", "idp_behavioral_responsibility",
    "parent_name", "parent_feedback",
    "overall_progress", "coach_summary_remarks",
]

RATING_FIELDS = [f for f in ASSESSMENT_FIELDS if f.endswith("_rating")]


def compute_age_and_focus(dob) -> tuple[int | None, str | None]:
    """REQ-003 / REQ-004: age + age-group focus, derived from DOB."""
    if not dob:
        return None, None
    if isinstance(dob, str):
        dob = datetime.strptime(dob, "%Y-%m-%d").date()
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if 6 <= age <= 10:
        focus = "Coordination & Agility"
    elif 11 <= age <= 14:
        focus = "Strength & Endurance"
    else:
        focus = None
    return age, focus


def compute_attendance_pct(planned, attended) -> float | None:
    """REQ-010: (Sessions Attended / Sessions Planned) * 100."""
    try:
        planned = int(planned)
        attended = int(attended)
    except (TypeError, ValueError):
        return None
    if planned <= 0:
        return None
    return round((attended / planned) * 100, 2)


def _assessment_tuple(data: dict) -> tuple:
    """Builds the positional tuple for the stored procs from a field dict,
    coercing '' -> None and rating fields -> int."""
    values = []
    for field in ASSESSMENT_FIELDS:
        val = data.get(field)
        if val == "":
            val = None
        if val is not None and field in RATING_FIELDS:
            val = int(val)
        values.append(val)
    return tuple(values)


def get_assessment_by_id(assessment_id: int) -> dict | None:
    rows = db.call_proc("sp_assessment_get_by_id", (assessment_id,))["rows"]
    return rows[0] if rows else None


def list_assessments(athlete_id=None, coach_id=None, status=None, is_archived=None) -> list[dict]:
    return db.call_proc(
        "sp_assessment_list", (athlete_id, coach_id, status, is_archived)
    )["rows"]


def get_latest_draft(athlete_id: int, coach_id: int) -> dict | None:
    rows = list_assessments(athlete_id=athlete_id, coach_id=coach_id, status="Draft", is_archived=False)
    return rows[0] if rows else None


def create_assessment(athlete_id: int, coach_id: int, assessment_date: str,
                       status: str, data: dict, created_by=None) -> int:
    args = (athlete_id, coach_id, assessment_date, status) + _assessment_tuple(data) + (created_by, None)
    result = db.call_proc("sp_assessment_create", args)
    # OUT param key matches the positional index of the placeholder arg
    # (the trailing None) in the args tuple — see Database.call_proc().
    return result["out_params"][f"p{len(args) - 1}"]


def update_assessment(assessment_id: int, status: str, data: dict):
    args = (assessment_id, status) + _assessment_tuple(data)
    db.call_proc("sp_assessment_update", args)


def archive_assessment(assessment_id: int, is_archived: bool):
    db.call_proc("sp_assessment_archive", (assessment_id, is_archived))


def delete_assessment(assessment_id: int):
    db.call_proc("sp_assessment_delete", (assessment_id,))


# ---------------------------------------------------------------------------
# Assessment Analytics
# ---------------------------------------------------------------------------

TALENT_CATEGORIES = ["Recreational", "Developing", "Potential Talent", "High Potential"]
PROGRESS_LEVELS = ["Excellent", "Good", "Average", "Need Attention"]


def _round_or_none(val, digits=1):
    return round(float(val), digits) if val is not None else None


def get_coach_analytics(coach_id: int, athlete_id: int | None = None, sport: str | None = None,
                         date_from: str | None = None, date_to: str | None = None) -> dict:
    """Aggregates everything the coach-wide Performance Analytics Dashboard
    needs into one dict. Each metric comes from its own single-result-set
    stored proc (see common/assessment_analytics.sql) since call_proc()
    only reads one result set per call.

    athlete_id / sport / date_from / date_to are optional filters (None = no
    filter) -- this is what powers the dashboard's filter bar. Passing an
    athlete_id narrows everything down to that single athlete; leaving it
    None keeps the dashboard aggregated across all of the coach's athletes."""

    filters = (athlete_id, sport, date_from or None, date_to or None)

    kpi_rows = db.call_proc("sp_analytics_kpis", (coach_id,) + filters)["rows"]
    kpi = kpi_rows[0] if kpi_rows else {}

    cat_rows = db.call_proc("sp_analytics_category_averages", (coach_id,) + filters)["rows"]
    categories = cat_rows[0] if cat_rows else {}

    talent_rows = db.call_proc("sp_analytics_talent_distribution", (coach_id,) + filters)["rows"]
    talent_counts = {row["talent_category"]: row["cnt"] for row in talent_rows}

    progress_rows = db.call_proc("sp_analytics_progress_distribution", (coach_id,) + filters)["rows"]
    progress_counts = {row["overall_progress"]: row["cnt"] for row in progress_rows}

    trend_rows = db.call_proc("sp_analytics_monthly_trend", (coach_id,) + filters)["rows"]

    return {
        "kpi": {
            "athlete_count": kpi.get("athlete_count") or 0,
            "total_assessments": kpi.get("total_assessments") or 0,
            "finalized_count": kpi.get("finalized_count") or 0,
            "draft_count": kpi.get("draft_count") or 0,
            "avg_attendance_pct": _round_or_none(kpi.get("avg_attendance_pct")),
            "avg_overall_rating": _round_or_none(kpi.get("avg_overall_rating"), 2),
        },
        "categories": {
            "labels": ["Physical", "Technical", "Tactical", "Behavioral"],
            "values": [
                _round_or_none(categories.get("avg_physical"), 2) or 0,
                _round_or_none(categories.get("avg_technical"), 2) or 0,
                _round_or_none(categories.get("avg_tactical"), 2) or 0,
                _round_or_none(categories.get("avg_behavioral"), 2) or 0,
            ],
        },
        "talent_distribution": {
            "labels": TALENT_CATEGORIES,
            "values": [talent_counts.get(cat, 0) for cat in TALENT_CATEGORIES],
        },
        "progress_distribution": {
            "labels": PROGRESS_LEVELS,
            "values": [progress_counts.get(p, 0) for p in PROGRESS_LEVELS],
        },
        "trend": {
            "labels": [row["month"] for row in trend_rows],
            "attendance_pct": [_round_or_none(row["avg_attendance_pct"]) or 0 for row in trend_rows],
            "overall_rating": [_round_or_none(row["avg_overall_rating"], 2) or 0 for row in trend_rows],
        },
    }


def get_athlete_analytics(athlete_id: int, coach_id: int) -> dict:
    """Same idea as get_coach_analytics(), but scoped to a single athlete —
    powers the per-athlete dashboard opened from the athlete list. Uses the
    procs in common/assessment_analytics_athlete.sql."""

    kpi_rows = db.call_proc("sp_analytics_athlete_kpis", (athlete_id, coach_id))["rows"]
    kpi = kpi_rows[0] if kpi_rows else {}

    latest_rows = db.call_proc("sp_analytics_athlete_latest", (athlete_id, coach_id))["rows"]
    latest = latest_rows[0] if latest_rows else {}

    trend_rows = db.call_proc("sp_analytics_athlete_trend", (athlete_id, coach_id))["rows"]
    cat_trend_rows = db.call_proc("sp_analytics_athlete_category_trend", (athlete_id, coach_id))["rows"]

    return {
        "kpi": {
            "total_assessments": kpi.get("total_assessments") or 0,
            "finalized_count": kpi.get("finalized_count") or 0,
            "draft_count": kpi.get("draft_count") or 0,
            "avg_attendance_pct": _round_or_none(kpi.get("avg_attendance_pct")),
            "avg_overall_rating": _round_or_none(kpi.get("avg_overall_rating"), 2),
            "latest_talent_category": latest.get("talent_category"),
            "latest_overall_progress": latest.get("overall_progress"),
            "latest_assessment_date": str(latest["assessment_date"]) if latest.get("assessment_date") else None,
        },
        "latest_snapshot": {
            "labels": ["Physical", "Technical", "Tactical", "Behavioral"],
            "values": [
                _round_or_none(latest.get("avg_physical"), 2) or 0,
                _round_or_none(latest.get("avg_technical"), 2) or 0,
                _round_or_none(latest.get("avg_tactical"), 2) or 0,
                _round_or_none(latest.get("avg_behavioral"), 2) or 0,
            ],
        },
        "trend": {
            "labels": [str(row["assessment_date"]) for row in trend_rows],
            "attendance_pct": [_round_or_none(row["attendance_pct"]) or 0 for row in trend_rows],
            "overall_rating": [_round_or_none(row["overall_rating"], 2) or 0 for row in trend_rows],
        },
        "category_trend": {
            "labels": [str(row["assessment_date"]) for row in cat_trend_rows],
            "physical": [_round_or_none(row["avg_physical"], 2) or 0 for row in cat_trend_rows],
            "technical": [_round_or_none(row["avg_technical"], 2) or 0 for row in cat_trend_rows],
            "tactical": [_round_or_none(row["avg_tactical"], 2) or 0 for row in cat_trend_rows],
            "behavioral": [_round_or_none(row["avg_behavioral"], 2) or 0 for row in cat_trend_rows],
        },
    }


# ---------------------------------------------------------------------------
# Squad-wide Performance Dashboard (roster-selector coach dashboard)
# ---------------------------------------------------------------------------

CATEGORY_LABELS = {"physical": "Physical", "technical": "Technical",
                   "tactical": "Tactical", "behavioral": "Behavioural"}
CATEGORY_WEIGHTS = {"physical": 0.25, "technical": 0.30, "tactical": 0.25, "behavioral": 0.20}


def _calc_perf_index(cat: dict) -> int:
    """Weighted 1-5 category ratings (25/30/25/20), scaled to a 0-100 index."""
    return round(
        (cat["physical"] * CATEGORY_WEIGHTS["physical"] +
         cat["technical"] * CATEGORY_WEIGHTS["technical"] +
         cat["tactical"] * CATEGORY_WEIGHTS["tactical"] +
         cat["behavioral"] * CATEGORY_WEIGHTS["behavioral"]) * 20
    )


def _build_recommendations(cat_current: dict, cat_prev: dict, attendance_pct: float | None) -> list[str]:
    """Short rule-based coaching notes generated from the athlete's own
    numbers -- lowest/highest category, direction of change, attendance."""
    recs = []
    if any(cat_current.values()):
        weakest = min(cat_current, key=lambda k: cat_current[k])
        strongest = max(cat_current, key=lambda k: cat_current[k])
        recs.append(
            f"{CATEGORY_LABELS[weakest]} rating ({cat_current[weakest]:.1f}) is the lowest of the four "
            f"categories — worth extra focus in upcoming sessions."
        )
        if strongest != weakest:
            recs.append(
                f"{CATEGORY_LABELS[strongest]} ({cat_current[strongest]:.1f}) stands out as a strength — "
                f"a good area to build confidence and lean on in competition."
            )

    delta = sum(cat_current.values()) - sum(cat_prev.values())
    if delta < -0.3:
        recs.append("Ratings have dipped since the last assessment — consider a 1:1 check-in to understand what's changed.")
    elif delta > 0.3:
        recs.append("Ratings have improved since the last assessment — the current training plan appears to be working well.")

    if attendance_pct is not None:
        if attendance_pct < 75:
            recs.append(f"Attendance is {round(attendance_pct)}%, below a healthy threshold — worth discussing barriers to attending sessions.")
        else:
            recs.append(f"Attendance is {round(attendance_pct)}%, a solid and consistent level.")

    return recs[:3]


def _latest_finalized_assessment(athlete_id: int, coach_id: int) -> dict | None:
    """Most recent non-Draft assessment (full row, incl. free-text fields) --
    used to enrich the Gemini recommendation prompt with the coach's own
    notes (strengths, improvements, talent category, summary remarks)."""
    rows = [r for r in list_assessments(athlete_id=athlete_id, coach_id=coach_id, is_archived=False)
            if r.get("status") != "Draft"]
    if not rows:
        return None
    rows.sort(key=lambda r: (r.get("assessment_date") or "", r.get("id") or 0), reverse=True)
    return rows[0]


def get_squad_performance_dashboard(coach_id: int) -> dict:
    """Powers the roster-selector Performance Dashboard: a pill per athlete,
    a profile card for whichever one is selected (client-side), and a squad
    comparison table -- all built from real assessment data rather than the
    original mock/demo dataset.

    Each athlete's "current" and "previous" category ratings are their most
    recent two *finalized* assessments (Drafts are excluded, same rule as
    the rest of the analytics). Attendance shown per-athlete is the
    attendance % of their most recent finalized assessments (this app
    doesn't log individual training-session attendance, so unlike a
    day-by-day P/L/A grid, each cell here represents one assessment period).
    """
    cats = list(CATEGORY_LABELS.keys())
    athletes_raw = list_athletes(coach_id=coach_id, is_archived=False)

    athletes = []
    for ath in athletes_raw:
        age, _ = compute_age_and_focus(ath.get("dob"))
        analytics = get_athlete_analytics(ath["id"], coach_id)
        cat_trend = analytics["category_trend"]
        att_series = analytics["trend"]["attendance_pct"]
        n = len(cat_trend["labels"])

        if n == 0:
            cat_current = {c: 0 for c in cats}
            cat_prev = dict(cat_current)
            index_trend = []
        else:
            cat_current = {c: cat_trend[c][-1] for c in cats}
            prev_i = -2 if n >= 2 else -1
            cat_prev = {c: cat_trend[c][prev_i] for c in cats}
            index_trend = [
                _calc_perf_index({c: cat_trend[c][i] for c in cats}) for i in range(n)
            ]

        index_current = _calc_perf_index(cat_current) if n else 0
        index_prev = _calc_perf_index(cat_prev) if n else 0
        avg_attendance = analytics["kpi"]["avg_attendance_pct"]

        recs = []

        athletes.append({
            "id": ath["id"],
            "name": ath["name"],
            "sport": ath.get("sport") or "-",
            "age": age,
            "has_data": n > 0,
            "has_prev": n >= 2,
            "cat": cat_current,
            "prev_cat": cat_prev,
            "trend": index_trend,
            "attendance_recent": att_series[-15:],
            "index": index_current,
            "delta": index_current - index_prev,
            "attendance_pct": round(avg_attendance) if avg_attendance is not None else None,
            "recs": recs,
        })

    max_len = max((len(a["trend"]) for a in athletes), default=0)
    squad_avg_trend = []
    for i in range(max_len):
        vals = [a["trend"][i] for a in athletes if len(a["trend"]) > i]
        squad_avg_trend.append(round(sum(vals) / len(vals)) if vals else 0)

    with_data = [a for a in athletes if a["has_data"]]
    squad_avg_index = round(sum(a["index"] for a in with_data) / len(with_data)) if with_data else 0

    return {
        "athletes": athletes,
        "squad_avg_index": squad_avg_index,
        "squad_avg_trend": squad_avg_trend,
    }


def get_athlete_recommendations(athlete_id: int, coach_id: int) -> list[str]:
    ath = get_athlete_by_id(athlete_id)
    if not ath or ath["coach_id"] != coach_id:
        return []

    age, _ = compute_age_and_focus(ath.get("dob"))
    analytics = get_athlete_analytics(athlete_id, coach_id)
    cat_trend = analytics["category_trend"]
    n = len(cat_trend["labels"])

    cats = list(CATEGORY_LABELS.keys())
    if n == 0:
        return []

    cat_current = {c: cat_trend[c][-1] for c in cats}
    prev_i = -2 if n >= 2 else -1
    cat_prev = {c: cat_trend[c][prev_i] for c in cats}
    avg_attendance = analytics["kpi"]["avg_attendance_pct"]

    latest_full = _latest_finalized_assessment(athlete_id, coach_id)
    recs = generate_coaching_recommendations(
        athlete_id=athlete_id, name=ath["name"], sport=ath.get("sport"), age=age,
        cat_current=cat_current, cat_prev=cat_prev, attendance_pct=avg_attendance,
        extra=latest_full or {}, fallback_fn=_build_recommendations,
    )
    return recs


# ---------------------------------------------------------------------------
# Coach-facing top-level Dashboard stats (dashboard.html)
# ---------------------------------------------------------------------------

def get_coach_dashboard_stats(coach_id: int) -> dict:
    """Powers the coach's top-level Dashboard: KPI cards (total athletes,
    total sports, total sessions planned/attended) + a sport-wise breakdown
    chart. Backed by sp_coach_dashboard_stats / sp_coach_dashboard_sport_breakdown
    (see common/coach_dashboard_stats.sql)."""

    kpi_rows = db.call_proc("sp_coach_dashboard_stats", (coach_id,))["rows"]
    kpi = kpi_rows[0] if kpi_rows else {}

    breakdown_rows = db.call_proc("sp_coach_dashboard_sport_breakdown", (coach_id,))["rows"]

    return {
        "athlete_count": kpi.get("athlete_count") or 0,
        "sport_count": kpi.get("sport_count") or 0,
        "sessions_planned_total": kpi.get("sessions_planned_total") or 0,
        "sessions_attended_total": kpi.get("sessions_attended_total") or 0,
        "sport_breakdown": {
            "labels": [row["sport"] for row in breakdown_rows],
            "athlete_counts": [row["athlete_count"] for row in breakdown_rows],
            "sessions_planned": [row["sessions_planned"] for row in breakdown_rows],
            "sessions_attended": [row["sessions_attended"] for row in breakdown_rows],
        },
    }


# ---------------------------------------------------------------------------
# Superadmin-facing top-level Dashboard stats (dashboard.html)
# ---------------------------------------------------------------------------

def get_superadmin_dashboard_stats() -> dict:
    """Powers the superadmin's top-level Dashboard: org-wide KPI cards
    (admins/coaches/athletes/sports/sessions) + a sport-wise breakdown
    across every coach. Backed by sp_superadmin_dashboard_stats /
    sp_superadmin_dashboard_sport_breakdown / sp_superadmin_dashboard_coach_sport_matrix
    (see common/superadmin_dashboard_stats.sql)."""

    kpi_rows = db.call_proc("sp_superadmin_dashboard_stats", ())["rows"]
    kpi = kpi_rows[0] if kpi_rows else {}

    breakdown_rows = db.call_proc("sp_superadmin_dashboard_sport_breakdown", ())["rows"]

    matrix_rows = db.call_proc("sp_superadmin_dashboard_coach_sport_matrix", ())["rows"]
    coaches_by_sport = {}
    for row in matrix_rows:
        coaches_by_sport.setdefault(row["coach_name"], {})[row["sport"]] = row["athlete_count"]
    sport_labels = [row["sport"] for row in breakdown_rows]
    coach_matrix = [
        {"coach_name": name, "counts": [sports.get(s, 0) for s in sport_labels]}
        for name, sports in sorted(coaches_by_sport.items())
    ]

    return {
        "admin_count": kpi.get("admin_count") or 0,
        "coach_count": kpi.get("coach_count") or 0,
        "athlete_count": kpi.get("athlete_count") or 0,
        "sport_count": kpi.get("sport_count") or 0,
        "sessions_planned_total": kpi.get("sessions_planned_total") or 0,
        "sessions_attended_total": kpi.get("sessions_attended_total") or 0,
        "avg_attendance_pct": _round_or_none(kpi.get("avg_attendance_pct"), 1),
        "sport_breakdown": {
            "labels": sport_labels,
            "athlete_counts": [row["athlete_count"] for row in breakdown_rows],
            "coach_counts": [row["coach_count"] for row in breakdown_rows],
            "sessions_planned": [row["sessions_planned"] for row in breakdown_rows],
            "sessions_attended": [row["sessions_attended"] for row in breakdown_rows],
            "avg_attendance_pct": [row["avg_attendance_pct"] or 0 for row in breakdown_rows],
        },
        "coach_sport_matrix": {
            "sports": sport_labels,
            "coaches": coach_matrix,
        },
    }


def get_superadmin_dashboard_stats_with_extras() -> dict:
    """get_superadmin_dashboard_stats() plus the shared leaderboard / age /
    activity widgets. Kept separate from get_superadmin_dashboard_stats()
    itself so existing callers are unaffected."""
    stats = get_superadmin_dashboard_stats()
    stats.update(_org_dashboard_extras())
    return stats


def _org_dashboard_extras() -> dict:
    """Shared by admin + superadmin dashboards: top-athlete leaderboard,
    age distribution, and recent activity (audit log). Backed by
    common/org_dashboard_extra.sql."""
    top_rows = db.call_proc("sp_org_dashboard_top_athletes", (10,))["rows"]
    age_rows = db.call_proc("sp_org_dashboard_age_distribution", ())["rows"]
    activity = list_audit_log(limit=8)

    return {
        "top_athletes": [
            {
                "athlete_id": r["athlete_id"],
                "athlete_name": r["athlete_name"],
                "sport": r["sport"] or "-",
                "coach_name": r["coach_name"],
                "avg_rating": _round_or_none(r["avg_rating"], 2),
                "attendance_pct": _round_or_none(r["attendance_pct"]),
                "talent_category": r["talent_category"],
            }
            for r in top_rows
        ],
        "age_distribution": {
            "labels": [r["age_group"] for r in age_rows],
            "values": [r["athlete_count"] for r in age_rows],
        },
        "recent_activity": activity,
    }


def get_admin_dashboard_stats() -> dict:
    """Powers the admin's premium top-level Dashboard: same org-wide KPI
    cards, sport-wise breakdown, top-athlete leaderboard, age distribution,
    and recent activity as the superadmin dashboard (admins share the same
    coach/athlete visibility, minus admin-account management)."""
    stats = get_superadmin_dashboard_stats()
    stats.update(_org_dashboard_extras())
    return stats


# ---------------------------------------------------------------------------
# Bootstrap default accounts (idempotent — safe to call on every app start)
# ---------------------------------------------------------------------------

def init_default_data():
    if not get_user_by_username("admin"):
        create_user(
            "admin",
            os.getenv("ADMIN_PASSWORD", "admin123"),
            "admin",
            os.getenv("ADMIN_NAME", "Admin User"),
            os.getenv("ADMIN_EMAIL", "admin@bjk.com"),
        )

    if not get_user_by_username("coach"):
        create_coach(
            "coach",
            os.getenv("COACH_PASSWORD", "coach123"),
            os.getenv("COACH_NAME", "Coach User"),
            os.getenv("COACH_EMAIL", "coach@bjk.com"),
            os.getenv("COACH_SPECIALTY", "General"),
        )
