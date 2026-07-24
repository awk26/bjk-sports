"""
Tests for the password-reset flow: forgot-password and reset-password routes.
"""
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytest
from flask import Flask
from werkzeug.test import Client

from werkzeug.security import check_password_hash
from bjk_athletes.models import USERS, reset_tokens


class TestForgotPassword:
    """GET and POST /forgot-password"""

    def test_forgot_password_page_returns_200(self, client: Client) -> None:
        """The forgot-password page should be served successfully."""
        resp = client.get("/forgot-password")
        assert resp.status_code == 200
        assert b"Forgot Password" in resp.data or b"Reset your password" in resp.data
        assert b"Send Reset Link" in resp.data

    def test_forgot_password_post_valid_user(self, client: Client) -> None:
        """A valid username should generate a token and redirect to login."""
        resp = client.post(
            "/forgot-password",
            data={"username": "admin"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"

        # Verify a token was created
        assert len(reset_tokens) == 1
        token, data = next(iter(reset_tokens.items()))
        assert data["username"] == "admin"
        assert "expires" in data
        assert data["expires"] > datetime.now()

    def test_forgot_password_post_invalid_user(self, client: Client) -> None:
        """An unknown username should still redirect (security: don't reveal user existence)."""
        resp = client.post(
            "/forgot-password",
            data={"username": "nonexistent"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"
        # No token should have been created
        assert len(reset_tokens) == 0

    def test_forgot_password_post_flash_confirmation(self, client: Client) -> None:
        """The success flash message should confirm the reset link was sent."""
        resp = client.post(
            "/forgot-password",
            data={"username": "admin"},
            follow_redirects=True,
        )
        assert b"reset link" in resp.data.lower()

    def test_forgot_password_post_invalid_also_flashes(self, client: Client) -> None:
        """Even for unknown users a flash message should be shown."""
        resp = client.post(
            "/forgot-password",
            data={"username": "unknown"},
            follow_redirects=True,
        )
        assert b"reset link" in resp.data.lower()


class TestResetPassword:
    """GET and POST /reset-password/<token>"""

    def _create_token(self, username: str = "admin", expire_hours: int = 1) -> str:
        """Helper: create a reset token and return it."""
        import secrets
        token = secrets.token_urlsafe(32)
        reset_tokens[token] = {
            "username": username,
            "expires": datetime.now() + timedelta(hours=expire_hours),
        }
        return token

    def test_reset_password_get_valid_token(self, client: Client) -> None:
        """A valid token should render the reset form."""
        token = self._create_token()
        resp = client.get(f"/reset-password/{token}")
        assert resp.status_code == 200
        assert b"Reset Password" in resp.data or b"Choose a new password" in resp.data

    def test_reset_password_post_valid(self, client: Client) -> None:
        """A valid submission should update the password, remove the token, and redirect."""
        token = self._create_token("admin")

        resp = client.post(
            f"/reset-password/{token}",
            data={"new_password": "newpass123", "confirm_password": "newpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"

        # Password should have been updated (now hashed)
        assert check_password_hash(USERS["admin"]["password"], "newpass123")
        # Token should be consumed
        assert token not in reset_tokens

    def test_reset_password_post_too_short(self, client: Client) -> None:
        """A password shorter than 6 characters should be rejected."""
        token = self._create_token("admin")

        resp = client.post(
            f"/reset-password/{token}",
            data={"new_password": "abc12", "confirm_password": "abc12"},
            follow_redirects=False,
        )
        assert resp.status_code == 200  # re-renders form
        assert b"at least 6 characters" in resp.data.lower()

        # Password should NOT have changed (still the hashed default)
        assert check_password_hash(USERS["admin"]["password"], "admin123")
        # Token should still exist
        assert token in reset_tokens

    def test_reset_password_post_passwords_mismatch(self, client: Client) -> None:
        """Non-matching passwords should be rejected."""
        token = self._create_token("admin")

        resp = client.post(
            f"/reset-password/{token}",
            data={"new_password": "newpass123", "confirm_password": "different"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"do not match" in resp.data.lower()

        # Password should NOT have changed (still the hashed default)
        assert check_password_hash(USERS["admin"]["password"], "admin123")
        # Token should still exist
        assert token in reset_tokens

    def test_reset_password_post_empty_password(self, client: Client) -> None:
        """An empty password should be rejected."""
        token = self._create_token("admin")

        resp = client.post(
            f"/reset-password/{token}",
            data={"new_password": "", "confirm_password": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"at least 6 characters" in resp.data.lower()

        # Token should still exist
        assert token in reset_tokens

    def test_reset_password_invalid_token(self, client: Client) -> None:
        """A non-existent token should redirect to login with an error."""
        resp = client.get("/reset-password/invalidtoken123", follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/login"

        resp2 = client.get("/reset-password/invalidtoken123", follow_redirects=True)
        assert b"Invalid or expired" in resp2.data

    def test_reset_password_expired_token(self, client: Client) -> None:
        """An expired token should redirect to forgot-password with an error."""
        token = self._create_token("admin", expire_hours=-2)  # expired 2 hours ago

        resp = client.get(f"/reset-password/{token}", follow_redirects=False)
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/forgot-password"

        resp2 = client.get(f"/reset-password/{token}", follow_redirects=True)
        assert b"expired" in resp2.data.lower()

        # The expired token should have been removed
        assert token not in reset_tokens

    def test_reset_password_expired_token_post(self, client: Client) -> None:
        """POSTing to an expired token should still redirect to forgot-password."""
        token = self._create_token("admin", expire_hours=-2)

        resp = client.post(
            f"/reset-password/{token}",
            data={"new_password": "newpass123", "confirm_password": "newpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        # Token was already expired -> popped on GET first? No, we directly POST.
        # The route checks expiry on POST as well, so redirect to forgot_password.
        path = urlparse(resp.location).path
        assert path == "/forgot-password"

    def test_reset_password_after_successful_reset_token_gone(self, client: Client) -> None:
        """After a successful password reset the same token should not work again."""
        token = self._create_token("admin")

        # First reset
        client.post(
            f"/reset-password/{token}",
            data={"new_password": "newpass123", "confirm_password": "newpass123"},
        )

        # Trying to use the same token again should fail
        resp = client.get(f"/reset-password/{token}", follow_redirects=True)
        assert b"Invalid or expired" in resp.data

    def test_reset_password_allows_login_with_new_password(self, client: Client) -> None:
        """After a reset, the user should be able to log in with the new password."""
        token = self._create_token("admin")

        # Reset password
        client.post(
            f"/reset-password/{token}",
            data={"new_password": "newpass123", "confirm_password": "newpass123"},
        )

        # Log out (not really needed since we have a fresh client) and log in with new password
        resp = client.post(
            "/login",
            data={"username": "admin", "password": "newpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert urlparse(resp.location).path == "/dashboard"

    def test_reset_password_old_password_no_longer_works(self, client: Client) -> None:
        """After a reset, the old password should not work."""
        token = self._create_token("admin")

        client.post(
            f"/reset-password/{token}",
            data={"new_password": "newpass123", "confirm_password": "newpass123"},
        )

        resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert resp.status_code == 200  # stays on login page
        assert b"Invalid username or password" in resp.data
