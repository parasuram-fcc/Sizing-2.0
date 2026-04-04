from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth  # Added: Google OAuth support

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
oauth = OAuth()  # Added: initialized in create_app via oauth.init_app(app)

login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
