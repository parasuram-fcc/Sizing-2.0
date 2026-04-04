from flask import Blueprint

bp = Blueprint("customer", __name__, url_prefix="/customer")

from app.blueprints.customer import routes  # noqa: F401, E402
