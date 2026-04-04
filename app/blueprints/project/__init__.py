from flask import Blueprint

bp = Blueprint("project", __name__, url_prefix="/project")

from app.blueprints.project import routes  # noqa: F401, E402
