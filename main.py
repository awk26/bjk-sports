import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, render_template, redirect, url_for, session, flash
from flask_wtf.csrf import CSRFProtect

from common.config import Config
from common.models import init_default_data
from common.decorators import login_required
from routes import auth, admin, coach, superadmin

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    csrf.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(coach.bp)
    app.register_blueprint(superadmin.bp)

    init_default_data()

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
    app.run(host='0.0.0.0',port=5003)
