"""Small SMTP helper for transactional email (password-reset OTP).

Configured from .env. The names checked first are the ones this project
uses; the MAIL_* fallbacks match the older variables that
models.send_assessment_email() already reads, so a single set of
credentials can serve both.

    SMTP_HOST      default smtp.gmail.com
    SMTP_PORT      default 587
    SMTP_USERNAME  the sending account
    SMTP_PASSWORD  or APP_PASSWORD -- for Gmail this must be an App Password,
                   not the account password (Google rejects the latter)
    SMTP_USE_TLS   default true
    SMTP_FROM      default = SMTP_USERNAME

send_email() returns True only when the message was actually handed to the
SMTP server, and never raises -- callers decide what to tell the user. The
reason for a failure goes to the app log rather than to the browser, since
it can contain server details.
"""
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from common.logs import log


def _cfg(*names, default=None):
    """First of `names` that is set to a non-empty value in the environment."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def smtp_settings() -> dict:
    username = _cfg("SMTP_USERNAME", "MAIL_USERNAME")
    return {
        "host": _cfg("SMTP_HOST", "MAIL_SERVER", default="smtp.gmail.com"),
        "port": int(_cfg("SMTP_PORT", "MAIL_PORT", default="587")),
        "username": username,
        # APP_PASSWORD is the usual name for a Gmail app password.
        "password": _cfg("SMTP_PASSWORD", "APP_PASSWORD", "MAIL_PASSWORD"),
        "use_tls": _cfg("SMTP_USE_TLS", "MAIL_USE_TLS", default="true").lower() == "true",
        "sender": _cfg("SMTP_FROM", "MAIL_DEFAULT_SENDER") or username,
        "sender_name": _cfg("SMTP_FROM_NAME", default="BJK Sports"),
    }


def is_configured() -> bool:
    """True when there are enough credentials to attempt a send."""
    cfg = smtp_settings()
    return bool(cfg["host"] and cfg["username"] and cfg["password"])


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True on success, False otherwise."""
    if not to_address:
        log("send_email: no recipient given")
        return False

    cfg = smtp_settings()
    if not is_configured():
        log("send_email: SMTP not configured (need SMTP_USERNAME and "
            "SMTP_PASSWORD/APP_PASSWORD) -- email not sent")
        return False

    msg = EmailMessage()
    msg["From"] = formataddr((cfg["sender_name"], cfg["sender"]))
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15) as server:
                server.login(cfg["username"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                if cfg["use_tls"]:
                    server.starttls()
                server.login(cfg["username"], cfg["password"])
                server.send_message(msg)
        return True
    except Exception as exc:
        # Logged, not surfaced: the message can leak host/account details.
        log(f"send_email: failed sending to {to_address}: {exc}")
        return False


def send_password_otp(to_address: str, otp: str, valid_minutes: int) -> bool:
    subject = "Your BJK Sports password reset code"
    body = (
        "We received a request to reset your BJK Sports password.\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code expires in {valid_minutes} minutes and can be used once.\n\n"
        "If you didn't request a password reset, you can ignore this email — "
        "your password stays unchanged.\n\n"
        "BJK Sports"
    )
    return send_email(to_address, subject, body)
