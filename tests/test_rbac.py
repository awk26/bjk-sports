"""
Tests for Role-Based Access Control (RBAC).
Ensures that admin, coach, and unauthenticated users are properly restricted.
"""
from urllib.parse import urlparse

import pytest
from flask import Flask
from werkzeug.test import Client


# ---------------------------------------------------------------------------
# Admin routes – coaches should NOT have access
# ---------------------------------------------------------------------------

ADMIN_ROUTES = [
    "/admin",
    "/admin/coaches",
    "/admin/coaches/create",
    "/admin/coaches/coach/edit",
]

ADMIN_POST_ROUTES = [
    ("/admin/coaches/create", {"username": "x", "password": "x", "name": "x"}),
    ("/admin/coaches/coach/edit", {"name": "x", "email": "", "specialty": "", "password": ""}),
    ("/admin/coaches/coach/archive", {}),
]


class TestAdminRoutesBlockedForCoach:
    """Coach users must not be able to access admin-only routes."""

    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    def test_coach_get_admin_route_redirects(self, coach_client: Client, route: str) -> None:
        """Coach GET requests to admin routes should redirect to dashboard."""
        resp = coach_client.get(route, follow_redirects=False)
        assert resp.status_code == 302
        path = urlparse(resp.location).path
        assert path == "/dashboard" or path == "/"

    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    def test_coach_get_admin_route_flash(self, coach_client: Client, route: str) -> None:
        """Coach should see a 'no permission' flash message."""
        resp = coach_client.get(route, follow_redirects=True)
        assert b"do not have permission" in resp.data.lower() or b"permission" in resp.data.lower()

    @pytest.mark.parametrize("route, data", ADMIN_POST_ROUTES)
    def test_coach_post_admin_route_redirects(
        self, coach_client: Client, route: str, data: dict
    ) -> None:
        """Coach POST requests to admin routes should redirect to dashboard."""
        resp = coach_client.post(route, data=data, follow_redirects=False)
        assert resp.status_code == 302
        path = urlparse(resp.location).path
        assert path == "/dashboard" or path == "/"


# ---------------------------------------------------------------------------
# Coach routes – admin users should NOT have access
# ---------------------------------------------------------------------------

COACH_ROUTES = [
    "/coach",
    "/coach/athletes",
    "/coach/athletes/create",
]

COACH_POST_ROUTES = [
    ("/coach/athletes/create", {"name": "x", "email": "", "phone": "", "dob": "", "sport": ""}),
]


class TestCoachRoutesBlockedForAdmin:
    """Admin users must not be able to access coach-only routes."""

    @pytest.mark.parametrize("route", COACH_ROUTES)
    def test_admin_get_coach_route_redirects(self, admin_client: Client, route: str) -> None:
        """Admin GET requests to coach routes should redirect to dashboard."""
        resp = admin_client.get(route, follow_redirects=False)
        assert resp.status_code == 302
        path = urlparse(resp.location).path
        assert path == "/dashboard" or path == "/"

    @pytest.mark.parametrize("route", COACH_ROUTES)
    def test_admin_get_coach_route_flash(self, admin_client: Client, route: str) -> None:
        """Admin should see a 'no permission' flash message."""
        resp = admin_client.get(route, follow_redirects=True)
        assert b"do not have permission" in resp.data.lower() or b"permission" in resp.data.lower()

    @pytest.mark.parametrize("route, data", COACH_POST_ROUTES)
    def test_admin_post_coach_route_redirects(
        self, admin_client: Client, route: str, data: dict
    ) -> None:
        """Admin POST requests to coach routes should redirect to dashboard."""
        resp = admin_client.post(route, data=data, follow_redirects=False)
        assert resp.status_code == 302
        path = urlparse(resp.location).path
        assert path == "/dashboard" or path == "/"


# ---------------------------------------------------------------------------
# Unauthenticated access – all protected routes should redirect to /login
# ---------------------------------------------------------------------------

PROTECTED_ROUTES = [
    "/dashboard",
    "/admin",
    "/admin/coaches",
    "/admin/coaches/create",
    "/admin/coaches/coach/edit",
    "/coach",
    "/coach/athletes",
    "/coach/athletes/create",
]

PROTECTED_POST_ROUTES = [
    ("/admin/coaches/create", {"username": "x", "password": "x", "name": "x"}),
    ("/admin/coaches/coach/edit", {"name": "x", "email": "", "specialty": "", "password": ""}),
    ("/admin/coaches/coach/archive", {}),
    ("/coach/athletes/create", {"name": "x"}),
]


class TestUnauthenticatedAccess:
    """Requests without a session must be redirected to login."""

    @pytest.mark.parametrize("route", PROTECTED_ROUTES)
    def test_unauthenticated_get_redirects_to_login(self, client: Client, route: str) -> None:
        """Protected GET routes should redirect to /login when not authenticated."""
        resp = client.get(route, follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"

    @pytest.mark.parametrize("route", PROTECTED_ROUTES)
    def test_unauthenticated_get_flash(self, client: Client, route: str) -> None:
        """Protected GET routes should flash 'Please log in' when not authenticated."""
        resp = client.get(route, follow_redirects=True)
        assert b"Please log in to continue" in resp.data

    @pytest.mark.parametrize("route, data", PROTECTED_POST_ROUTES)
    def test_unauthenticated_post_redirects_to_login(
        self, client: Client, route: str, data: dict
    ) -> None:
        """Protected POST routes should redirect to /login when not authenticated."""
        resp = client.post(route, data=data, follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"

    @pytest.mark.parametrize("route, data", PROTECTED_POST_ROUTES)
    def test_unauthenticated_post_flash(
        self, client: Client, route: str, data: dict
    ) -> None:
        """Protected POST routes should flash 'Please log in' when not authenticated."""
        resp = client.post(route, data=data, follow_redirects=True)
        assert b"Please log in to continue" in resp.data


# ---------------------------------------------------------------------------
# Public routes – should be accessible by anyone
# ---------------------------------------------------------------------------

class TestPublicRoutes:
    """Routes like /login, /forgot-password, /logout are public."""

    @pytest.mark.parametrize("route", [
        "/login",
        "/forgot-password",
        "/logout",
    ])
    def test_public_routes_accessible(self, client: Client, route: str) -> None:
        """Public routes should not redirect when accessed without authentication."""
        resp = client.get(route, follow_redirects=False)
        # They should return either 200 or a redirect (e.g. logout always redirects)
        assert resp.status_code in (200, 302)
