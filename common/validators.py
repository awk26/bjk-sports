"""Shared required-field rules for the athlete and coach add/edit forms.

Kept in one place because the same form is rendered (and posted) from three
different blueprints -- admin, coach and superadmin -- and the rules have to
agree across all of them. Each function returns a list of human-readable
labels for whatever is missing, so the route can flash them straight back.

The labels here mirror the red `*` markers in the templates: anything listed
below is marked required in the form, and nothing marked required in the form
is missing from here.
"""

REQUIRED_ATHLETE_FIELDS = [
    ("first_name", "First name"),
    ("last_name", "Last name"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("dob", "Date of birth"),
    ("gender", "Gender"),
    ("blood_group", "Blood group"),
    ("emergency_contact_name", "Emergency contact name"),
    ("emergency_contact_phone", "Emergency contact phone"),
    ("parent_name", "Parent / guardian name"),
]

REQUIRED_COACH_FIELDS = [
    ("first_name", "First name"),
    ("last_name", "Last name"),
    ("email", "Email"),
    ("phone", "Phone"),
]


def _missing(form, fields) -> list[str]:
    return [label for field, label in fields if not (form.get(field) or "").strip()]


def missing_athlete_fields(form, sport_ids=None) -> list[str]:
    """Required fields for Add/Edit Athlete, including at least one sport."""
    missing = _missing(form, REQUIRED_ATHLETE_FIELDS)
    if not sport_ids:
        missing.append("At least one sport")
    return missing


def missing_coach_fields(form, sport_ids=None) -> list[str]:
    """Required fields for Add/Edit Coach, including at least one sport."""
    missing = _missing(form, REQUIRED_COACH_FIELDS)
    if not sport_ids:
        missing.append("At least one sport")
    return missing


def missing_fields_message(missing: list[str]) -> str:
    """Flash-ready sentence listing what still needs filling in."""
    return "Please fill in the required field(s): " + ", ".join(missing) + "."
