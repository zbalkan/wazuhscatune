#!/usr/bin/env python3

"""Flask application entry point for wazuhscatune."""
import copy
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
HOST: Final[str] = "127.0.0.1"
PORT: Final[int] = 5000

ANSI_ESCAPE_RE: re.Pattern[str] = re.compile(
    r"""
    (?:
      \x1B\[
      [0-?]*[ -/]*[@-~]
     |
      \x1B[@-Z\\-_]
     |
      \x1B\][^\x07]*(?:\x07|\x1B\\)
     |
      (?:\\x1[bB]|\<0x1[bB]\>)(?:\[[0-?]*[ -/]*[@-~])?
    )
    """,
    re.VERBOSE,
)


class SanitizingFormatter(logging.Formatter):
    """Format a sanitized copy without mutating the shared log record."""

    def format(self, record: logging.LogRecord) -> str:
        sanitized = copy.copy(record)
        sanitized.msg = ANSI_ESCAPE_RE.sub('', sanitized.getMessage())
        sanitized.args = ()
        if sanitized.name == 'root':
            sanitized.name = APP_NAME
        return super().format(sanitized)


def _get_log_path() -> str:
    """Return a per-user log file path for Windows, Linux, and macOS."""
    if os.name == "nt":
        base_dir = os.getenv(
            "LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        log_dir = os.path.join(base_dir, APP_NAME, "Logs")
    elif sys.platform == "darwin":
        log_dir = os.path.expanduser(f"~/Library/Logs/{APP_NAME}")
    else:
        xdg_state_home = os.getenv(
            "XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
        log_dir = os.path.join(xdg_state_home, APP_NAME)
        if not os.access(os.path.dirname(log_dir), os.W_OK):
            log_dir = os.path.expanduser(f"~/.local/share/{APP_NAME}/logs")

    os.makedirs(log_dir, exist_ok=True)
    return os.path.abspath(os.path.join(log_dir, f"{APP_NAME}.log"))


def _hide_server_banner(*args, **kwargs) -> None:
    """Suppress Flask's development-server banner for this local helper."""
    return None


def create_app(config_class=Config) -> Flask:
    """Create and configure the Flask application."""
    cli = sys.modules.get('flask.cli')
    if cli is not None:
        cli.show_server_banner = _hide_server_banner  # type: ignore[attr-defined]

    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DRAFT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    Session(app)

    SessionService.cleanup_expired(
        [app.config['UPLOAD_FOLDER'], app.config['DRAFT_FOLDER'],
         app.config['EXPORT_FOLDER'], app.config['SESSION_FILE_DIR']],
        app.config['FILE_TTL_HOURS'])

    app.register_blueprint(upload_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(export_bp)

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
    """Open the app's URL in the user's default browser, if available."""
    try:
        if webbrowser.get().name != 'gio':
            webbrowser.open_new(url)
    except webbrowser.Error:
        pass
    print(f"Access the app over {url}")


def _configure_logging() -> None:
    """Write application logs to a per-user file and suppress Flask clutter."""
    handler = logging.FileHandler(_get_log_path(), encoding=ENCODING)
    handler.setFormatter(SanitizingFormatter(
        fmt='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    ))
    logging.basicConfig(
        handlers=[handler],
        level=logging.INFO,
        force=True,
    )
    logging.getLogger('werkzeug').disabled = True


def main() -> None:
    """Run the single-user local web helper."""
    try:
        _configure_logging()
        logging.info('Starting')

        app = create_app()
        url = f'http://{HOST}:{PORT}/'
        Timer(1, _open_browser, args=(url,)).start()

        logging.info("Starting Flask app...")
        app.run(debug=False, use_reloader=False, host=HOST, port=PORT)
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


if __name__ == '__main__':
    main()
