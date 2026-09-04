#!/usr/bin/env python3

"""Flask application entry point for wazuhscatune."""
import logging
import os
import re
import sys
import webbrowser
from threading import Timer
from typing import Final

from flask import Flask, render_template
from flask_session import Session

from sca.config import Config
from sca.routes.export import export_bp
from sca.routes.review import review_bp
from sca.routes.upload import upload_bp
from sca.services.session_service import SessionService

APP_NAME: Final[str] = Config.APP_NAME
ENCODING: Final[str] = "utf-8"

# Precompiled regex to remove ANSI color/control sequences
ANSI_ESCAPE_RE: re.Pattern[str] = re.compile(
    r"""
    (?:                           # Non-capturing group for all patterns
      \x1B\[                      # ESC [ (CSI)
      [0-?]*[ -/]*[@-~]           # Parameter bytes + intermediate + final byte
     |                            # OR
      \x1B[@-Z\\-_]               # 2-byte sequences
     |                            # OR
      \x1B\][^\x07]*(?:\x07|\x1B\\) # OSC sequences
     |                            # OR literal representations (\x1b, <0x1b>)
      (?:\\x1[bB]|\<0x1[bB]\>)(?:\[[0-?]*[ -/]*[@-~])?
    )
    """,
    re.VERBOSE,
)


class CustomFileHandler(logging.FileHandler):
    """FileHandler that strips all escape sequences and representations."""

    def emit(self, record) -> None:
        record.msg = ANSI_ESCAPE_RE.sub('', str(record.msg))  # Escape ANSI Color Sequences
        super().emit(record)


def _get_log_path() -> str:
    """
    Return a per-user log file path appropriate for Windows, Linux, and macOS.
    Uses only os and sys modules.
    """
    # Determine base OS type
    if os.name == "nt":  # Windows
        base_dir = os.getenv(
            "LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        log_dir = os.path.join(base_dir, APP_NAME, "Logs")

    elif sys.platform == "darwin":  # macOS
        log_dir = os.path.expanduser(f"~/Library/Logs/{APP_NAME}")

    else:  # Linux / other Unix-like
        xdg_state_home = os.getenv(
            "XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
        log_dir = os.path.join(xdg_state_home, APP_NAME)
        if not os.access(os.path.dirname(log_dir), os.W_OK):
            log_dir = os.path.expanduser(f"~/.local/share/{APP_NAME}/logs")

    os.makedirs(log_dir, exist_ok=True)
    return os.path.abspath(os.path.join(log_dir, f"{APP_NAME}.log"))


def create_app(config_class=Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DRAFT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    Session(app)

    SessionService.cleanup_expired(
        [app.config['UPLOAD_FOLDER'], app.config['DRAFT_FOLDER'],
         app.config['EXPORT_FOLDER'], app.config['SESSION_FILE_DIR']],
        app.config['FILE_TTL_HOURS'])

    # Register blueprints
    app.register_blueprint(upload_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(export_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return {'error': 'File too large. Maximum size is 16MB.'}, 413

    return app


def _open_browser(url: str) -> None:
    """Open the app's URL in the user's default browser, if one is available."""
    try:
        if webbrowser.get().name != 'gio':
            webbrowser.open_new(url)
    except webbrowser.Error:
        pass
    print(f"Access the app over {url}")


def main() -> None:
    """Run the local web application."""
    app = create_app()
    is_development = os.environ.get('FLASK_ENV') == 'development'
    host = '0.0.0.0' if is_development else '127.0.0.1'
    port = 5000

    # Avoid opening a second browser tab when the reloader respawns the process.
    if not is_development or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1, _open_browser, args=(f'http://127.0.0.1:{port}/',)).start()

    logging.info("Starting Flask app...")
    app.run(debug=is_development, host=host, port=port)


if __name__ == '__main__':
    try:
        handler = CustomFileHandler(_get_log_path(), encoding=ENCODING)

        logging.basicConfig(handlers=[handler],
                            format='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
                            datefmt="%Y-%m-%dT%H:%M:%S%z",
                            level=logging.INFO)
        # Get the loggers used by Flask and prevent them from propagating to the root logger
        wl = logging.getLogger('werkzeug')
        wl.disabled = True
        excepthook = logging.error
        logging.info('Starting')
        main()
        logging.info('Exiting.')
    except KeyboardInterrupt:
        print('Cancelled by user.')
        logging.info('Cancelled by user.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as ex:
        print('ERROR: ' + str(ex))
        logging.error(str(ex), exc_info=True)
        try:
            sys.exit(1)
        except SystemExit:
            os._exit(1)
