from flask import Blueprint

bp = Blueprint("noise", __name__, url_prefix="/noise")

from app.blueprints.noise import routes  # noqa: F401, E402
