import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, render_template, redirect, url_for, session, flash, g, request, jsonify
from flask_wtf.csrf import CSRFProtect

from common.config import Config
from common.models import init_default_data
from common.decorators import login_required
from routes import auth, admin, coach, superadmin
from common.models import (
    get_coach_dashboard_stats,
    get_admin_dashboard_stats,
    get_superadmin_dashboard_stats_with_extras,
    list_athletes,
    list_coaches,
    list_users,
)

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
            f"style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
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
        user = session["user"]
        coach_stats = admin_stats = sa_stats = None
        if user["role"] == "coach":
            coach_stats = get_coach_dashboard_stats(user["coach_id"])
        elif user["role"] == "admin":
            admin_stats = get_admin_dashboard_stats()
        elif user["role"] == "superadmin":
            sa_stats = get_superadmin_dashboard_stats_with_extras()
        return render_template("dashboard.html", user=user,
                                coach_stats=coach_stats, admin_stats=admin_stats, sa_stats=sa_stats)
    
    
    
    @app.route("/api/search")
    @login_required
    def api_search():
        """
        Role-aware live search endpoint.
        Returns JSON: { results: [ {type, label, sub, url}, ... ] }
        Searches athletes (all roles), coaches (admin/superadmin),
        and admin users (superadmin only).
        """
        q = request.args.get("q", "").strip().lower()
        if not q or len(q) < 1:
            return jsonify(results=[])

        user = session["user"]
        role = user["role"]
        results = []

        # ---- Athletes ----
        try:
            if role == "coach":
                athletes = list_athletes(coach_id=user.get("coach_id"), is_archived=False)
            else:
                athletes = list_athletes(is_archived=False)

            for a in athletes:
                name = (a.get("name") or "").lower()
                sport = (a.get("sport") or "").lower()
                code = (a.get("athlete_code") or "").lower()
                if q in name or q in sport or q in code:
                    if role == "coach":
                        url = url_for("coach.coach_athlete_edit", athlete_id=a["id"])
                    elif role == "admin":
                        url = url_for("admin.admin_athletes")
                    else:
                        url = url_for("superadmin.superadmin_athletes")
                    results.append({
                        "type": "athlete",
                        "icon": "bi-person-lines-fill",
                        "label": a.get("name", ""),
                        "sub": a.get("sport") or "Athlete",
                        "url": url,
                    })
        except Exception:
            pass

        # ---- Coaches (admin + superadmin) ----
        if role in ("admin", "superadmin"):
            try:
                coaches = list_coaches(is_archived=False)
                for c in coaches:
                    name = (c.get("name") or "").lower()
                    spec = (c.get("specialty") or "").lower()
                    username = (c.get("username") or "").lower()
                    if q in name or q in spec or q in username:
                        if role == "admin":
                            url = url_for("admin.admin_coaches")
                        else:
                            url = url_for("superadmin.superadmin_coaches")
                        results.append({
                            "type": "coach",
                            "icon": "bi-people",
                            "label": c.get("name", ""),
                            "sub": c.get("specialty") or "Coach",
                            "url": url,
                        })
            except Exception:
                pass

        # ---- Admin users (superadmin only) ----
        if role == "superadmin":
            try:
                admins = list_users(role="admin", is_archived=False)
                for ad in admins:
                    name = (ad.get("name") or "").lower()
                    username = (ad.get("username") or "").lower()
                    email = (ad.get("email") or "").lower()
                    if q in name or q in username or q in email:
                        results.append({
                            "type": "admin",
                            "icon": "bi-person-badge",
                            "label": ad.get("name", ""),
                            "sub": f"@{ad.get('username', '')} · Admin",
                            "url": url_for("superadmin.superadmin_admins"),
                        })
            except Exception:
                pass

        # Cap to 8 results
        return jsonify(results=results[:8])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5003)