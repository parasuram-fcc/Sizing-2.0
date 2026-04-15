import os
from dotenv import load_dotenv
import json

load_dotenv()

env_file = os.path.join(os.path.dirname(__file__), "env.json")
with open(env_file, 'r') as f:
    env_data = json.load(f)

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", env_data['SECRET_KEY'])
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", env_data['DATABASE_URL'])
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get("MAIL_SERVER", env_data['MAIL_SERVER'])
    MAIL_PORT = int(os.environ.get("MAIL_PORT", env_data['MAIL_PORT']))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", env_data['MAIL_USERNAME'])
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", env_data['MAIL_PASSWORD'])
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", env_data['MAIL_DEFAULT_SENDER'])
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), "exports")
    DATA_FOLDER = os.path.join(os.path.dirname(__file__), "data")

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    QOUTE_RANGE = os.environ.get("QOUTE_RANGE", env_data["QOUTE_RANGE"]) # in years

class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class ElectronConfig(Config):
    """SQLite-backed config for the Electron desktop bundle."""
    DEBUG = False

    # Store the database and user files in %APPDATA%\ValveSizing (Windows)
    # or ~/.ValveSizing (macOS/Linux)
    _user_data = os.path.join(
        os.environ.get('APPDATA', os.path.expanduser('~')),
        'ValveSizing'
    )
    os.makedirs(_user_data, exist_ok=True)

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_user_data, 'valvesizing.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLite doesn't need pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {}

    # Re-point upload/export folders to user data dir so they survive app updates
    UPLOAD_FOLDER = os.path.join(_user_data, 'uploads')
    EXPORT_FOLDER = os.path.join(_user_data, 'exports')

    # Email is optional in desktop mode; disable to avoid startup errors
    # MAIL_SERVER = None


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "electron": ElectronConfig,
    "default": DevelopmentConfig,
}
