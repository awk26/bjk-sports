"""
Tests for coach routes: coach panel, athlete management, and archiving.
"""
from urllib.parse import urlparse

import pytest
from flask import Flask
from werkzeug.test import Client

from werkzeug.security import generate_password_hash
from bjk_athletes.models import ATHLETES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_athlete(client: Client, name: str = "Test Athlete", **overrides) -> str:
    """Helper to create an athlete and return its ID."""
    data = {
        "name": name,
        "email": "athlete@test.com",
        "phone": "1234567890",
        "dob": "2000-01-15",
        "sport": "Soccer",
    }
    data.update(overrides)
    resp = client.post("/coach/athletes/create", data=data, follow_redirects=False)
    assert resp.status_code == 302
    # Find the athlete that was just created (last one)
    for aid, a in ATHLETES.items():
        if a["name"] == name:
            return aid
    raise AssertionError(f"Athlete '{name}' was not found in ATHLETES after creation.")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCoachPanel:
    """GET /coach"""

    def test_coach_panel_accessible_by_coach(self, coach_client: Client) -> None:
        """The coach panel should render for an authenticated coach."""
        resp = coach_client.get("/coach")
        assert resp.status_code == 200
        assert b"Coach" in resp.data or b"coach" in resp.data.lower()

    def test_coach_panel_shows_no_athletes_initially(self, coach_client: Client) -> None:
        """The coach panel should indicate no athletes when none exist."""
        resp = coach_client.get("/coach")
        # Should not show any athlete entries when empty
        assert resp.status_code == 200


class TestCoachAthletesList:
    """GET /coach/athletes"""

    def test_athletes_list_empty(self, coach_client: Client) -> None:
        """The athletes list should render even when there are no athletes."""
        resp = coach_client.get("/coach/athletes")
        assert resp.status_code == 200

    def test_athletes_list_shows_created_athletes(self, coach_client: Client) -> None:
        """Athletes belonging to the coach should be listed."""
        _create_athlete(coach_client, "Alice")
        _create_athlete(coach_client, "Bob")

        resp = coach_client.get("/coach/athletes")
        assert resp.status_code == 200
        assert b"Alice" in resp.data
        assert b"Bob" in resp.data

    def test_athletes_list_does_not_show_other_coach_athletes(
        self, coach_client: Client, client: Client
    ) -> None:
        """A coach should only see their own athletes, not those of other coaches."""
        # Create athlete for coach_user
        _create_athlete(coach_client, "Coach's Athlete")

        # Create a second coach and log in as them
        from bjk_athletes.models import USERS, COACHES
        USERS["coach2"] = {
            "password": generate_password_hash("pass1234"), "role": "coach",
            "name": "Second Coach", "email": "coach2@bjk.com",
        }
        COACHES["coach2"] = {"specialty": "Tennis", "is_archived": False}

        client.post("/login", data={"username": "coach2", "password": "pass1234"})
        resp = client.get("/coach/athletes")
        assert b"Coach's Athlete" not in resp.data


class TestCoachAthleteCreate:
    """GET and POST /coach/athletes/create"""

    def test_create_page_renders(self, coach_client: Client) -> None:
        """The create-athlete form should render."""
        resp = coach_client.get("/coach/athletes/create")
        assert resp.status_code == 200

    def test_create_athlete_valid(self, coach_client: Client) -> None:
        """Creating an athlete with all fields should succeed."""
        resp = coach_client.post(
            "/coach/athletes/create",
            data={
                "name": "New Athlete",
                "email": "new@test.com",
                "phone": "9876543210",
                "dob": "1999-12-25",
                "sport": "Basketball",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/coach/athletes"

        # Verify athlete exists
        athletes = [a for a in ATHLETES.values() if a["name"] == "New Athlete"]
        assert len(athletes) == 1
        athlete = athletes[0]
        assert athlete["email"] == "new@test.com"
        assert athlete["phone"] == "9876543210"
        assert athlete["dob"] == "1999-12-25"
        assert athlete["sport"] == "Basketball"
        assert athlete["coach_username"] == "coach"
        assert athlete["is_archived"] is False
        assert athlete["id"].startswith("ATH-")

    def test_create_athlete_missing_name(self, coach_client: Client) -> None:
        """A missing athlete name should show an error."""
        resp = coach_client.post(
            "/coach/athletes/create",
            data={
                "name": "",
                "email": "",
                "phone": "",
                "dob": "",
                "sport": "",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"required" in resp.data.lower() or b"name" in resp.data.lower()
        assert len(ATHLETES) == 0

    def test_create_athlete_minimal_fields(self, coach_client: Client) -> None:
        """Creating an athlete with just a name should succeed."""
        resp = coach_client.post(
            "/coach/athletes/create",
            data={"name": "Minimal", "email": "", "phone": "", "dob": "", "sport": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "Minimal" in [a["name"] for a in ATHLETES.values()]

    def test_athlete_id_increments(self, coach_client: Client) -> None:
        """Each athlete should get a unique, incrementing ID."""
        id1 = _create_athlete(coach_client, "First")
        id2 = _create_athlete(coach_client, "Second")
        assert id1 != id2
        # ATH-001, ATH-002 format
        assert id1 == "ATH-001"
        assert id2 == "ATH-002"


class TestCoachAthleteEdit:
    """GET and POST /coach/athletes/<athlete_id>/edit"""

    def test_edit_page_renders(self, coach_client: Client) -> None:
        """The edit-athlete form should be pre-populated."""
        aid = _create_athlete(coach_client, "Editable")
        resp = coach_client.get(f"/coach/athletes/{aid}/edit")
        assert resp.status_code == 200
        assert b"Editable" in resp.data

    def test_edit_athlete_valid(self, coach_client: Client) -> None:
        """Updating athlete details should persist."""
        aid = _create_athlete(coach_client, "Original Name")
        resp = coach_client.post(
            f"/coach/athletes/{aid}/edit",
            data={
                "name": "Updated Name",
                "email": "updated@test.com",
                "phone": "1112223333",
                "dob": "1998-06-15",
                "sport": "Tennis",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/coach/athletes"

        athlete = ATHLETES[aid]
        assert athlete["name"] == "Updated Name"
        assert athlete["email"] == "updated@test.com"
        assert athlete["phone"] == "1112223333"
        assert athlete["dob"] == "1998-06-15"
        assert athlete["sport"] == "Tennis"

    def test_edit_athlete_missing_name(self, coach_client: Client) -> None:
        """An empty name should show an error."""
        aid = _create_athlete(coach_client, "No Name Please")
        resp = coach_client.post(
            f"/coach/athletes/{aid}/edit",
            data={"name": "", "email": "", "phone": "", "dob": "", "sport": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"required" in resp.data.lower() or b"name" in resp.data.lower()
        # Original name should remain
        assert ATHLETES[aid]["name"] == "No Name Please"

    def test_edit_non_existent_athlete(self, coach_client: Client) -> None:
        """Editing a non-existent athlete should redirect with an error."""
        resp = coach_client.get("/coach/athletes/ATH-999/edit", follow_redirects=True)
        assert b"not found" in resp.data.lower()

    def test_edit_athlete_of_another_coach(self, coach_client: Client, client: Client) -> None:
        """A coach should not be able to edit another coach's athlete."""
        aid = _create_athlete(coach_client, "Secret Athlete")

        # Log in as a different coach
        from bjk_athletes.models import USERS, COACHES
        USERS["coach2"] = {
            "password": generate_password_hash("pass1234"), "role": "coach",
            "name": "Second Coach", "email": "coach2@bjk.com",
        }
        COACHES["coach2"] = {"specialty": "Tennis", "is_archived": False}
        client.post("/login", data={"username": "coach2", "password": "pass1234"})

        resp = client.get(f"/coach/athletes/{aid}/edit", follow_redirects=True)
        assert b"not found" in resp.data.lower()


class TestCoachAthleteArchive:
    """POST /coach/athletes/<athlete_id>/archive"""

    def test_archive_athlete(self, coach_client: Client) -> None:
        """Archiving an athlete should flip is_archived to True."""
        aid = _create_athlete(coach_client, "Archivable")
        assert ATHLETES[aid]["is_archived"] is False

        resp = coach_client.post(f"/coach/athletes/{aid}/archive", follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/coach/athletes"
        assert ATHLETES[aid]["is_archived"] is True

    def test_unarchive_athlete(self, coach_client: Client) -> None:
        """Archiving an already-archived athlete should unarchive them."""
        aid = _create_athlete(coach_client, "Unarchivable")
        ATHLETES[aid]["is_archived"] = True

        coach_client.post(f"/coach/athletes/{aid}/archive")
        assert ATHLETES[aid]["is_archived"] is False

    def test_archive_non_existent_athlete(self, coach_client: Client) -> None:
        """Archiving a non-existent athlete should redirect with an error."""
        resp = coach_client.post("/coach/athletes/ATH-999/archive", follow_redirects=True)
        assert b"not found" in resp.data.lower()

    def test_archive_athlete_of_another_coach(self, coach_client: Client, client: Client) -> None:
        """A coach should not be able to archive another coach's athlete."""
        aid = _create_athlete(coach_client, "Not Yours")

        from bjk_athletes.models import USERS, COACHES
        USERS["coach2"] = {
            "password": generate_password_hash("pass1234"), "role": "coach",
            "name": "Second Coach", "email": "coach2@bjk.com",
        }
        COACHES["coach2"] = {"specialty": "Tennis", "is_archived": False}
        client.post("/login", data={"username": "coach2", "password": "pass1234"})

        resp = client.post(f"/coach/athletes/{aid}/archive", follow_redirects=True)
        assert b"not found" in resp.data.lower()
