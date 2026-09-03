from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from common.decorators import login_required, role_required
from common.models import list_events, get_event_by_id, create_event, update_event, archive_event, log_audit

bp = Blueprint("events", __name__, url_prefix="/events")


@bp.route("/")
@login_required
def events_list():
    role = session["user"]["role"]
    level_filter = request.args.get("level") or "all"
    search = (request.args.get("q") or "").strip()

    events = list_events(level=level_filter if level_filter != "all" else None, is_archived=False, search=search)

    # Separate into upcoming and past
    from datetime import date
    today = date.today()
    upcoming_events = []
    past_events = []

    for ev in events:
        ev_date = ev.get("event_date")
        if isinstance(ev_date, str):
            try:
                ev_date = date.fromisoformat(ev_date)
            except Exception:
                ev_date = today
        if ev_date >= today:
            upcoming_events.append(ev)
        else:
            past_events.append(ev)

    can_manage = role in ["superadmin", "admin"]
    return render_template(
        "events.html",
        upcoming_events=upcoming_events,
        past_events=past_events,
        events=events,
        level_filter=level_filter,
        search=search,
        can_manage=can_manage,
        user=session["user"]
    )


@bp.route("/add", methods=["POST"])
@login_required
@role_required("superadmin", "admin")
def add_event():
    event_name = request.form.get("event_name", "").strip()
    description = request.form.get("description", "").strip()
    event_date = request.form.get("event_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    location = request.form.get("location", "").strip()
    level = request.form.get("level", "District").strip()

    if not event_name or not event_date or not location:
        flash("Event name, date, and location are required.", "danger")
        return redirect(url_for("events.events_list"))

    event_id = create_event(
        event_name=event_name,
        description=description,
        event_date=event_date,
        location=location,
        level=level,
        end_date=end_date or None,
        created_by=session["user"].get("id")
    )
    log_audit(
        actor_username=session["user"]["username"],
        actor_role=session["user"]["role"],
        action="CREATE_EVENT",
        target_type="EVENT",
        target_id=event_id,
        details=f"Created event '{event_name}' ({level})"
    )
    flash(f"Event '{event_name}' created successfully!", "success")
    return redirect(url_for("events.events_list"))


@bp.route("/edit/<int:id>", methods=["POST"])
@login_required
@role_required("superadmin", "admin")
def edit_event(id):
    event = get_event_by_id(id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("events.events_list"))

    event_name = request.form.get("event_name", "").strip()
    description = request.form.get("description", "").strip()
    event_date = request.form.get("event_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    location = request.form.get("location", "").strip()
    level = request.form.get("level", "District").strip()

    if not event_name or not event_date or not location:
        flash("Event name, date, and location are required.", "danger")
        return redirect(url_for("events.events_list"))

    update_event(
        event_id=id,
        event_name=event_name,
        description=description,
        event_date=event_date,
        location=location,
        level=level,
        end_date=end_date or None
    )
    log_audit(
        actor_username=session["user"]["username"],
        actor_role=session["user"]["role"],
        action="UPDATE_EVENT",
        target_type="EVENT",
        target_id=id,
        details=f"Updated event #{id} '{event_name}'"
    )
    flash(f"Event '{event_name}' updated successfully!", "success")
    return redirect(url_for("events.events_list"))


@bp.route("/archive/<int:id>", methods=["POST"])
@login_required
@role_required("superadmin", "admin")
def delete_event(id):
    event = get_event_by_id(id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("events.events_list"))

    archive_event(id, is_archived=True)
    log_audit(
        actor_username=session["user"]["username"],
        actor_role=session["user"]["role"],
        action="ARCHIVE_EVENT",
        target_type="EVENT",
        target_id=id,
        details=f"Archived event #{id} '{event['event_name']}'"
    )
    flash(f"Event '{event['event_name']}' archived successfully.", "info")
    return redirect(url_for("events.events_list"))
