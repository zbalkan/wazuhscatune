#!/usr/bin/env python3

"""Flask application entry point for wazuhscatune."""
import os

from flask import Flask, render_template

from sca.config import Config
from sca.routes.export import export_bp
from sca.routes.review import review_bp
from sca.routes.upload import upload_bp


def create_app(config_class=Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DRAFT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

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


if __name__ == '__main__':
    app = create_app()
    # Only enable debug mode and external access in development
    is_development = os.environ.get('FLASK_ENV') == 'development'
    app.run(
        debug=is_development,
        host='127.0.0.1' if not is_development else '0.0.0.0',
        port=5000
    )
