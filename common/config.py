import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(64).hex())
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1")
    PERMANENT_SESSION_LIFETIME = 28800

    # --- Super Admin -------------------------------------------------
    # Hardcoded credentials as requested. The super admin is NOT stored
    # in the USERS dict / users table — it authenticates directly
    # against these values. Override via environment variables in any
    # real deployment; do not ship the default password to production.
    SUPERADMIN_USERNAME = os.getenv("SUPERADMIN_USERNAME", "superadmin")
    SUPERADMIN_PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "SuperAdmin@123")
