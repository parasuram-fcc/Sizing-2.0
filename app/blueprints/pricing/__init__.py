from flask import Blueprint

bp = Blueprint("pricing", __name__, url_prefix="/pricing")

from app.blueprints.pricing import routes  # noqa: F401, E402
