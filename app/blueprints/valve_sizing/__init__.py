from flask import Blueprint

bp = Blueprint("valve_sizing", __name__, url_prefix="/sizing")

from app.blueprints.valve_sizing import routes  # noqa: F401, E402
