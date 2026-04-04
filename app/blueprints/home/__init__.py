from flask import Blueprint

bp = Blueprint("home", __name__)

from app.blueprints.home import routes  # noqa: F401, E402
