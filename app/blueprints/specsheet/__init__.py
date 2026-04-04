from flask import Blueprint

bp = Blueprint("specsheet", __name__, url_prefix="/specsheet")

from app.blueprints.specsheet import routes  # noqa: F401, E402
