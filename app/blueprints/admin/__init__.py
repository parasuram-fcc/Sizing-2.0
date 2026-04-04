from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

from app.blueprints.admin import routes  # noqa: F401, E402
