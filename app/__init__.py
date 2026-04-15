import re
import sqlite3
from flask import Flask, render_template
from sqlalchemy import event
from sqlalchemy.engine import Engine
from config import config_map


# ---------------------------------------------------------------------------
# SQLite compatibility shims
# Register functions that exist in PostgreSQL but not in SQLite so that
# queries using func.right() and .regexp_match() work on both databases.
# ---------------------------------------------------------------------------
@event.listens_for(Engine, "connect")
def _register_sqlite_functions(dbapi_connection, connection_record):
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    # RIGHT(str, n) — last n characters
    dbapi_connection.create_function(
        "right", 2,
        lambda s, n: s[-n:] if s else ""
    )
    # REGEXP — used by SQLAlchemy's .regexp_match()
    def _regexp(pattern, value):
        if value is None:
            return False
        return bool(re.search(pattern, str(value)))
    dbapi_connection.create_function("regexp", 2, _regexp)


def create_app(config_name="default"):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_map[config_name])

    # Initialize extensions
    from app.extensions import db, login_manager, mail, migrate, oauth
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)  # Added: Google OAuth

    # Register Google OAuth client (credentials from app config / environment)
    oauth.register(
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile", "clock_skew": 300},
    )

    # Register custom Jinja filters
    @app.template_filter('url_path')
    def url_path(url):
        # Returns the first path segment: "/home/proj-1/item-2" → "home"
        return url.split('/')[1] if url else ''

    # Register blueprints
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.admin import bp as admin_bp
    from app.blueprints.home import bp as home_bp
    from app.blueprints.project import bp as project_bp
    from app.blueprints.customer import bp as customer_bp
    from app.blueprints.valve_sizing import bp as valve_sizing_bp
    from app.blueprints.actuator import bp as actuator_bp
    from app.blueprints.noise import bp as noise_bp
    from app.blueprints.specsheet import bp as specsheet_bp
    from app.blueprints.pricing import bp as pricing_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(valve_sizing_bp)
    app.register_blueprint(actuator_bp)
    app.register_blueprint(noise_bp)
    app.register_blueprint(specsheet_bp)
    app.register_blueprint(pricing_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    return app
