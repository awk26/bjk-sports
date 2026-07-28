import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, render_template, redirect, url_for, session, flash, g, request
from flask_wtf.csrf import CSRFProtect

from common.config import Config
from common.models import init_default_data
from common.decorators import login_required
from routes import auth, admin, coach, superadmin

csrf = CSRFProtect()

# Paths that should never be cached by the browser (VAPT: "Re-examine
# Cache-control Directives" -- login page and all authenticated areas).
_NO_CACHE_PREFIXES = ("/login", "/dashboard", "/coach/", "/admin/", "/superadmin/")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    csrf.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(coach.bp)
    app.register_blueprint(superadmin.bp)

    init_default_data()

    @app.before_request
    def set_csp_nonce():
        # A fresh nonce per request; inline <script>/<style> tags in
        # templates must carry nonce="{{ csp_nonce() }}" to be allowed
        # once 'unsafe-inline' is removed from the CSP below.
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def inject_csp_nonce():
        return {"csp_nonce": lambda: g.csp_nonce}

    @app.after_request
    def set_security_headers(resp):
        nonce = g.get("csp_nonce", "")
        resp.headers["Content-Security-Policy"] = (
            f"default-src 'self' blob:; "
            f"script-src 'self' https://cdnjs.cloudflare.com https://fonts.googleapis.com 'nonce-{nonce}'; "
            f"style-src 'self' https://cdnjs.cloudflare.com https://fonts.googleapis.com 'nonce-{nonce}'; "
            f"img-src 'self' data: blob: https://cdnjs.cloudflare.com; "
            f"font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            f"connect-src 'self' https://api.anthropic.com https://accounts.google.com https://oauth2.googleapis.com; "
            f"frame-ancestors 'self'; form-action 'self'; object-src 'self' blob:; "
            f"frame-src 'self' blob:; base-uri 'self';"
        )

        if request.path == "/" or request.path.startswith(_NO_CACHE_PREFIXES):
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return resp

    @app.errorhandler(404)
    def not_found(e):
        return render_template("base.html", title="Not Found"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("base.html", title="Server Error"), 500

    @app.route("/")
    def index():
        if "user" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("auth.login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html", user=session["user"])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5003)