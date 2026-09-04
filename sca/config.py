import os
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version

try:
    VERSION = version('wazuhscatune')
except PackageNotFoundError:
    VERSION = '0+unknown'


class Config:
    """Flask application configuration."""

    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        # In development, generate a random key
        # In production, this should be set via environment variable
        if os.environ.get('FLASK_ENV') == 'production':
            raise ValueError("SECRET_KEY environment variable must be set in production")
        else:
            SECRET_KEY = os.urandom(24).hex()

    # Upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    DRAFT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drafts')
    EXPORT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'yml', 'yaml'}

    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flask_session')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    FILE_TTL_HOURS = int(os.environ.get('WAZUHSCATUNE_FILE_TTL_HOURS', '48'))
    # Auto-detect production environment for secure cookies
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Application info
    APP_NAME = 'wazuhscatune'
    APP_VERSION = VERSION
