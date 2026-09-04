#!/usr/bin/env python3

"""Flask application entry point for wazuhscatune."""
import os
import webbrowser
from threading import Timer

from flask import Flask, render_template
from flask_session import Session

from sca.config import Config
from sca.routes.export import export_bp
from sca.routes.review import review_bp
from sca.routes.upload import upload_bp
from sca.services.session_service import SessionService


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

    app.run(debug=is_development, host=host, port=port)


if __name__ == '__main__':
    main()
