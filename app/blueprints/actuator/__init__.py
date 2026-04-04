from flask import Blueprint

bp = Blueprint("actuator", __name__, url_prefix="/actuator")

from app.blueprints.actuator import routes  # noqa: F401, E402
