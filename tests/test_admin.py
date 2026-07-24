"""
Tests for admin routes: admin panel, coach management, and archiving.
"""
from urllib.parse import urlparse

import pytest
from flask import Flask
from werkzeug.test import Client

from werkzeug.security import check_password_hash
from bjk_athletes.models import USERS, COACHES


class TestAdminPanel:
    """GET /admin"""

    def test_admin_panel_accessible_by_admin(self, admin_client: Client) -> None:
        """The admin panel should render for an authenticated admin."""
        resp = admin_client.get("/admin")
        assert resp.status_code == 200
        assert b"Admin" in resp.data

    def test_admin_panel_shows_coach_count(self, admin_client: Client) -> None:
        """The admin panel should contain data about users/coaches."""
        resp = admin_client.get("/admin")
        assert b"coach" in resp.data.lower()


class TestAdminCoachesList:
    """GET /admin/coaches"""

    def test_coaches_list_renders(self, admin_client: Client) -> None:
        """The coaches list page should display coach information."""
        resp = admin_client.get("/admin/coaches")
        assert resp.status_code == 200
        # The default coach should appear
        assert b"Coach User" in resp.data
        assert b"coach" in resp.data

    def test_coaches_list_shows_archive_status(self, admin_client: Client) -> None:
        """The list should indicate whether a coach is archived."""
        resp = admin_client.get("/admin/coaches")
        assert resp.status_code == 200
        # Not archived by default
        assert b"archived" not in resp.data.lower() or b"unarchived" in resp.data.lower()


class TestAdminCoachCreate:
    """GET and POST /admin/coaches/create"""

    def test_create_page_renders(self, admin_client: Client) -> None:
        """The create-coach form should render."""
        resp = admin_client.get("/admin/coaches/create")
        assert resp.status_code == 200
        assert b"Create" in resp.data or b"Coach" in resp.data

    def test_create_coach_valid(self, admin_client: Client) -> None:
        """Creating a coach with all required fields should succeed."""
        resp = admin_client.post(
            "/admin/coaches/create",
            data={
                "username": "newcoach",
                "password": "pass1234",
                "name": "New Coach",
                "email": "new@bjk.com",
                "specialty": "Swimming",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/admin/coaches"

        # Verify the coach was added to USERS and COACHES
        assert "newcoach" in USERS
        assert USERS["newcoach"]["role"] == "coach"
        assert USERS["newcoach"]["name"] == "New Coach"
        assert USERS["newcoach"]["email"] == "new@bjk.com"
        assert "newcoach" in COACHES
        assert COACHES["newcoach"]["specialty"] == "Swimming"
        assert COACHES["newcoach"]["is_archived"] is False

    def test_create_coach_missing_username(self, admin_client: Client) -> None:
        """Missing username should show an error and not create the coach."""
        resp = admin_client.post(
            "/admin/coaches/create",
            data={"username": "", "password": "pass1234", "name": "No Name"},
            follow_redirects=False,
        )
        assert resp.status_code == 200  # re-renders form
        assert b"required" in resp.data.lower()

        assert "No Name" not in [u["name"] for u in USERS.values() if u["role"] == "coach"]

    def test_create_coach_missing_password(self, admin_client: Client) -> None:
        """Missing password should show an error."""
        resp = admin_client.post(
            "/admin/coaches/create",
            data={"username": "nopass", "password": "", "name": "No Pass"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"required" in resp.data.lower()
        assert "nopass" not in USERS

    def test_create_coach_missing_name(self, admin_client: Client) -> None:
        """Missing name should show an error."""
        resp = admin_client.post(
            "/admin/coaches/create",
            data={"username": "noname", "password": "pass1234", "name": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"required" in resp.data.lower()
        assert "noname" not in USERS

    def test_create_coach_duplicate_username(self, admin_client: Client) -> None:
        """Creating a coach with an existing username should fail."""
        resp = admin_client.post(
            "/admin/coaches/create",
            data={
                "username": "coach",
                "password": "pass1234",
                "name": "Duplicate Coach",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"already exists" in resp.data.lower()

    def test_create_coach_optional_fields(self, admin_client: Client) -> None:
        """Email and specialty are optional; the coach should still be created."""
        resp = admin_client.post(
            "/admin/coaches/create",
            data={
                "username": "minimal",
                "password": "pass1234",
                "name": "Minimal Coach",
                "email": "",
                "specialty": "",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "minimal" in USERS
        assert COACHES["minimal"]["specialty"] == ""


class TestAdminCoachEdit:
    """GET and POST /admin/coaches/<username>/edit"""

    def test_edit_page_renders(self, admin_client: Client) -> None:
        """The edit-coach form should be pre-populated with current data."""
        resp = admin_client.get("/admin/coaches/coach/edit")
        assert resp.status_code == 200
        assert b"Coach User" in resp.data or b"coach" in resp.data.lower()

    def test_edit_coach_valid(self, admin_client: Client) -> None:
        """Updating coach details should persist the changes."""
        resp = admin_client.post(
            "/admin/coaches/coach/edit",
            data={
                "name": "Updated Coach",
                "email": "updated@bjk.com",
                "specialty": "Basketball",
                "password": "",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/admin/coaches"

        assert USERS["coach"]["name"] == "Updated Coach"
        assert USERS["coach"]["email"] == "updated@bjk.com"
        assert COACHES["coach"]["specialty"] == "Basketball"

    def test_edit_coach_change_password(self, admin_client: Client) -> None:
        """Providing a new password should update it."""
        admin_client.post(
            "/admin/coaches/coach/edit",
            data={
                "name": "Coach User",
                "email": "coach@bjk.com",
                "specialty": "General",
                "password": "newpassword",
            },
        )
        assert check_password_hash(USERS["coach"]["password"], "newpassword")

    def test_edit_coach_empty_name_rejected(self, admin_client: Client) -> None:
        """An empty name should show an error."""
        resp = admin_client.post(
            "/admin/coaches/coach/edit",
            data={
                "name": "",
                "email": "",
                "specialty": "",
                "password": "",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"required" in resp.data.lower() or b"name" in resp.data.lower()

    def test_edit_non_existent_coach(self, admin_client: Client) -> None:
        """Editing a non-existent coach should redirect with an error."""
        resp = admin_client.get("/admin/coaches/nonexistent/edit", follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/admin/coaches"

        resp2 = admin_client.get("/admin/coaches/nonexistent/edit", follow_redirects=True)
        assert b"not found" in resp2.data.lower()

    def test_edit_coach_preserves_archive_status(self, admin_client: Client) -> None:
        """Editing a coach should not alter their archive status."""
        COACHES["coach"]["is_archived"] = True

        admin_client.post(
            "/admin/coaches/coach/edit",
            data={
                "name": "Coach User",
                "email": "coach@bjk.com",
                "specialty": "General",
                "password": "",
            },
        )
        # Archive status should still be True
        assert COACHES["coach"]["is_archived"] is True


class TestAdminCoachArchive:
    """POST /admin/coaches/<username>/archive"""

    def test_archive_coach_toggle(self, admin_client: Client) -> None:
        """Archiving a coach should set is_archived to True."""
        assert COACHES["coach"]["is_archived"] is False

        resp = admin_client.post("/admin/coaches/coach/archive", follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/admin/coaches"
        assert COACHES["coach"]["is_archived"] is True

    def test_unarchive_coach(self, admin_client: Client) -> None:
        """Archiving an already-archived coach should unarchive them."""
        COACHES["coach"]["is_archived"] = True

        admin_client.post("/admin/coaches/coach/archive")
        assert COACHES["coach"]["is_archived"] is False

    def test_archive_non_existent_coach(self, admin_client: Client) -> None:
        """Archiving a non-existent coach should redirect with an error."""
        resp = admin_client.post("/admin/coaches/nonexistent/archive", follow_redirects=True)
        assert b"not found" in resp.data.lower()

    def test_archive_admin_not_allowed(self, admin_client: Client) -> None:
        """Attempting to archive a user who is not a coach should show 'not found'."""
        resp = admin_client.post("/admin/coaches/admin/archive", follow_redirects=True)
        assert b"not found" in resp.data.lower()


class TestAdminCoachAccessOnAdminUser:
    """Admin-only routes should be inaccessible to non-admin users."""

    def test_coaches_list_admin_only(self, client: Client) -> None:
        """The coach listing should require admin role."""
        # Log in as coach
        client.post("/login", data={"username": "coach", "password": "coach123"})
        resp = client.get("/admin/coaches", follow_redirects=True)
        assert b"do not have permission" in resp.data.lower() or b"permission" in resp.data.lower()
    def test_coach_create_admin_only(self, client: Client) -> None:
        """The coach create page should require admin role."""
        client.post("/login", data={"username": "coach", "password": "coach123"})
        resp = client.get("/admin/coaches/create", follow_redirects=True)
        assert b"do not have permission" in resp.data.lower() or b"permission" in resp.data.lower()
