"""Upload routes - File upload and validation."""
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Literal

from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, session, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from werkzeug.wrappers.response import Response as wResponse

from sca.services.sca_service import SCAService
from sca.services.session_service import SessionService, contained_path

upload_bp = Blueprint('upload', __name__)
logger: logging.Logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def sanitize_policy_name(name: str) -> str:
    """
    Sanitize policy name for use as filename.
    - Convert to lowercase
    - Remove problematic punctuation
    - Replace spaces with underscores
    - Remove leading/trailing underscores

    Example: "Company Windows 11 Hardening Policy" -> "company_windows_11_hardening_policy"
    """
    if not name:
        return ''

    # Convert to lowercase
    sanitized: str = name.lower()

    # Keep only alphanumeric, spaces, hyphens, and underscores
    sanitized = re.sub(r'[^a-z0-9\s\-_]', '', sanitized)

    # Replace multiple spaces/hyphens with single space
    sanitized = re.sub(r'[\s\-]+', ' ', sanitized)

    # Trim whitespace
    sanitized = sanitized.strip()

    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')

    # Remove leading/trailing underscores
    sanitized = re.sub(r'^_+|_+$', '', sanitized)

    return sanitized


@upload_bp.route('/')
def index() -> str:
    """Landing page with upload form."""
    drafts: list[dict[str, Any]] = SessionService(current_app.config['DRAFT_FOLDER']).list_drafts()
    return render_template('index.html', drafts=drafts)


@upload_bp.route('/upload', methods=['POST'])
def upload_file() -> tuple[Response, Literal[400]] | Response | tuple[Response, Literal[500]]:
    """Handle file upload, validation, and session initialization."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file: FileStorage = request.files['file']

        if file.filename == '' or file.filename is None:
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only .yml and .yaml files are allowed'}), 400

        # Get custom policy details
        custom_name: str = request.form.get('custom_name', '').strip()
        custom_description: str = request.form.get('custom_description', '').strip()

        # Validate inputs
        if not custom_name or len(custom_name) < 15 or len(custom_name) > 100:
            return jsonify({'error': 'Policy name must be between 15 and 100 characters'}), 400

        if not custom_description or len(custom_description) < 50 or len(custom_description) > 500:
            return jsonify({'error': 'Policy description must be between 50 and 500 characters'}), 400

        # Save uploaded file
        filename: str = secure_filename(file.filename)
        session_id = str(uuid.uuid4())
        filepath: str = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")

        try:
            file.save(filepath)

            # Validate SCA file
            is_valid, error_msg = SCAService.validate_sca_file(filepath)
            if not is_valid:
                os.remove(filepath)
                return jsonify({'error': f'Invalid SCA file: {error_msg}'}), 400

            # Sanitize policy name for filename
            sanitized_name: str = sanitize_policy_name(custom_name)
            if not sanitized_name:
                os.remove(filepath)
                return jsonify({'error': 'Policy name contains no valid characters for filename'}), 400

            # Initialize session
            session['session_id'] = session_id
            session['baseline_filename'] = os.path.basename(filepath)
            session['custom_name'] = custom_name
            session['sanitized_name'] = sanitized_name  # Store sanitized name for file generation
            session['custom_description'] = custom_description
            session['decisions'] = {}
            session.permanent = True

            # Save draft
            session_service = SessionService(current_app.config['DRAFT_FOLDER'])
            session_data = SessionService.serialize_session_data(
                os.path.basename(filepath), custom_name, sanitized_name,
                custom_description, {}
            )
            session_service.save_draft(session_id, session_data)

            return jsonify({
                'success': True,
                'redirect': url_for('review.review_page'),
                'recovery_url': url_for('upload.recover_draft', session_id=session_id)
            })
        except Exception:
            # Clean up uploaded file on error
            if os.path.exists(filepath):
                os.remove(filepath)
            raise

    except Exception:
        logger.exception("Unable to upload SCA file")
        return jsonify({'error': 'Unable to process SCA file.'}), 500


@upload_bp.route('/validate', methods=['POST'])
def validate_file() -> tuple[Response, Literal[400]] | Response | tuple[Response, Literal[500]]:
    """AJAX endpoint for file validation."""
    try:
        if 'file' not in request.files:
            return jsonify({'valid': False, 'error': 'No file provided'}), 400

        file: FileStorage = request.files['file']

        if file.filename == '' or file.filename is None:
            return jsonify({'valid': False, 'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'valid': False, 'error': 'Invalid file type'}), 400

        # Save to temporary location for validation
        filename: str = secure_filename(file.filename)
        validation_id = str(uuid.uuid4())
        temp_path: str = os.path.join(current_app.config['UPLOAD_FOLDER'], f"validate_{validation_id}_{filename}")
        try:
            file.save(temp_path)
            is_valid, error_msg = SCAService.validate_sca_file(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        if is_valid:
            return jsonify({'valid': True})
        else:
            return jsonify({'valid': False, 'error': error_msg})

    except Exception:
        logger.exception("Unable to validate SCA file")
        return jsonify({'valid': False, 'error': 'Unable to validate SCA file.'}), 500


@upload_bp.route('/recover/<session_id>')
def recover_draft(session_id: str) -> tuple[Response, Literal[404]] | tuple[Response, Literal[410]] | wResponse | tuple[Response, Literal[400]]:
    """Restore a locally persisted review draft."""
    service = SessionService(current_app.config['DRAFT_FOLDER'])
    data: dict[str, Any] | None = service.load_draft(session_id)
    if not data:
        return jsonify({'error': 'Draft not found'}), 404
    try:
        filename = str(data['baseline_filename'])
        path: Path = contained_path(current_app.config['UPLOAD_FOLDER'], filename)
        if not path.is_file():
            return jsonify({'error': 'Draft baseline is no longer available'}), 410
        session.clear()
        session.update(session_id=session_id, baseline_filename=filename,
                       custom_name=data['custom_name'],
                       sanitized_name=data['sanitized_name'],
                       custom_description=data['custom_description'],
                       decisions=data.get('decisions', {}))
        session.permanent = True
        return redirect(url_for('review.review_page'))
    except (KeyError, TypeError, ValueError):
        logger.warning("Invalid draft data for %s", session_id, exc_info=True)
        return jsonify({'error': 'Draft is invalid'}), 400
