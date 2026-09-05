import os
import sys
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    VERSION = version('wazuhscatune')
except PackageNotFoundError:
    VERSION = '0+unknown'

APP_NAME = 'wazuhscatune'


def _default_data_root() -> Path:
    override = os.environ.get('WAZUHSCATUNE_DATA_DIR')
    if override:
        return Path(override).expanduser().resolve()
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser(r'~\AppData\Local')))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share')))
    return (base / APP_NAME).resolve()


DATA_ROOT = _default_data_root()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if os.environ.get('FLASK_ENV') == 'production':
            raise ValueError("SECRET_KEY environment variable must be set in production")
        SECRET_KEY = os.urandom(24).hex()

    UPLOAD_FOLDER = str(DATA_ROOT / 'uploads')
    DRAFT_FOLDER = str(DATA_ROOT / 'drafts')
    EXPORT_FOLDER = str(DATA_ROOT / 'exports')
    SESSION_FILE_DIR = str(DATA_ROOT / 'flask_session')
    LOG_FOLDER = str(DATA_ROOT / 'logs')

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'yml', 'yaml'}
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    FILE_TTL_HOURS = int(os.environ.get('WAZUHSCATUNE_FILE_TTL_HOURS', '48'))
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    APP_NAME = APP_NAME
    APP_VERSION = VERSION
