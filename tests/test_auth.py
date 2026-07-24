"""
Tests for authentication routes: login, logout, and basic access control.
"""
from urllib.parse import urlparse

import pytest
from flask import Flask
from werkzeug.test import Client


class TestLogin:
    """GET and POST /login"""

    def test_login_page_returns_200(self, client: Client) -> None:
        """The login page should be served successfully."""
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"BJK SPORTS" in resp.data
        assert b"Sign In" in resp.data

    def test_login_valid_admin_redirects_and_flash(self, client: Client) -> None:
        """Admin credentials should log the user in and redirect to dashboard."""
        resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        path = urlparse(resp.location).path
        assert path == "/dashboard"

        # Follow the redirect and check the flash message
        resp2 = client.get("/dashboard")
        assert b"Welcome back, Admin User" in resp2.data

    def test_login_valid_coach_redirects_and_flash(self, client: Client) -> None:
        """Coach credentials should log the user in and redirect to dashboard."""
        resp = client.post(
            "/login",
            data={"username": "coach", "password": "coach123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        path = urlparse(resp.location).path
        assert path == "/dashboard"

        resp2 = client.get("/dashboard")
        assert b"Welcome back, Coach User" in resp2.data

    def test_login_invalid_credentials_stays_on_page(self, client: Client) -> None:
        """Bad credentials should re-render login with an error flash."""
        resp = client.post(
            "/login",
            data={"username": "admin", "password": "wrongpassword"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"Invalid username or password" in resp.data

    def test_login_missing_fields(self, client: Client) -> None:
        """Missing username/password should still be handled gracefully."""
        resp = client.post(
            "/login",
            data={"username": "", "password": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"Invalid username or password" in resp.data

    def test_login_archived_coach_rejected(self, client: Client) -> None:
        """An archived coach should not be allowed to log in."""
        # First archive the coach
        from bjk_athletes.models import COACHES
        COACHES["coach"]["is_archived"] = True

        resp = client.post(
            "/login",
            data={"username": "coach", "password": "coach123"},
            follow_redirects=False,
        )
        assert resp.status_code == 200  # re-renders login
        assert b"deactivated" in resp.data.lower() or b"contact an administrator" in resp.data.lower()

    def test_login_archived_coach_not_affect_admin(self, client: Client) -> None:
        """Archiving a coach should not affect admin login."""
        from bjk_athletes.models import COACHES
        COACHES["coach"]["is_archived"] = True

        resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/dashboard"

    def test_login_sets_session_user(self, client: Client) -> None:
        """After successful login the session should contain user info."""
        client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        with client.session_transaction() as sess:
            assert "user" in sess
            assert sess["user"]["username"] == "admin"
            assert sess["user"]["role"] == "admin"
            assert sess["user"]["name"] == "Admin User"


class TestLogout:
    """GET /logout"""

    def test_logout_clears_session_and_redirects(self, client: Client) -> None:
        """Logging out should clear the session and redirect to login."""
        # Log in first
        client.post("/login", data={"username": "admin", "password": "admin123"})

        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"

        # Session should be cleared
        with client.session_transaction() as sess:
            assert "user" not in sess

    def test_logout_flash_message(self, client: Client) -> None:
        """The logout flash should inform the user."""
        client.post("/login", data={"username": "admin", "password": "admin123"})
        resp = client.get("/logout", follow_redirects=True)
        assert b"logged out" in resp.data.lower()

    def test_logout_when_not_logged_in(self, client: Client) -> None:
        """Logging out when not logged in should still work."""
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"


class TestIndex:
    """GET /"""

    def test_index_redirects_authenticated_user_to_dashboard(self, client: Client) -> None:
        """Logged-in users hitting / should go to /dashboard."""
        client.post("/login", data={"username": "admin", "password": "admin123"})
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/dashboard"

    def test_index_redirects_unauthenticated_user_to_login(self, client: Client) -> None:
        """Users who are not logged in hitting / should go to /login."""
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"


class TestAccessControl:
    """Protected routes should redirect unauthenticated users."""

    @pytest.mark.parametrize("route", [
        "/dashboard",
        "/admin",
        "/coach",
        "/admin/coaches",
        "/admin/coaches/create",
        "/coach/athletes",
        "/coach/athletes/create",
    ])
    def test_unauthenticated_access_redirects_to_login(self, client: Client, route: str) -> None:
        """Accessing any protected route without a session should redirect to /login."""
        resp = client.get(route, follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"

    @pytest.mark.parametrize("route", [
        "/dashboard",
        "/admin",
        "/coach",
        "/admin/coaches",
        "/admin/coaches/create",
        "/coach/athletes",
        "/coach/athletes/create",
    ])
    def test_unauthenticated_access_flash_message(self, client: Client, route: str) -> None:
        """An unauthenticated user should see a 'please log in' flash."""
        resp = client.get(route, follow_redirects=True)
        assert b"Please log in to continue" in resp.data
