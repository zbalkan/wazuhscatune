"""Upload and draft lifecycle routes."""
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
logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def sanitize_policy_name(name: str) -> str:
    sanitized = re.sub(r'[^a-z0-9\s\-_]', '', name.lower())
    sanitized = re.sub(r'[\s\-]+', ' ', sanitized).strip().replace(' ', '_')
    return re.sub(r'^_+|_+$', '', sanitized)


@upload_bp.route('/')
def index() -> str:
    drafts: list[dict[str, Any]] = SessionService(current_app.config['DRAFT_FOLDER']).list_drafts()
    return render_template('index.html', drafts=drafts)


@upload_bp.route('/upload', methods=['POST'])
def upload_file() -> tuple[Response, Literal[400]] | Response | tuple[Response, Literal[500]]:
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file: FileStorage = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only .yml and .yaml files are allowed'}), 400

        custom_name = request.form.get('custom_name', '').strip()
        custom_description = request.form.get('custom_description', '').strip()
        if not 15 <= len(custom_name) <= 100:
            return jsonify({'error': 'Policy name must be between 15 and 100 characters'}), 400
        if not 50 <= len(custom_description) <= 500:
            return jsonify({'error': 'Policy description must be between 50 and 500 characters'}), 400

        session_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
        try:
            file.save(filepath)
            is_valid, error_msg = SCAService.validate_sca_file(filepath)
            if not is_valid:
                os.remove(filepath)
                return jsonify({'error': f'Invalid SCA file: {error_msg}'}), 400

            sanitized_name = sanitize_policy_name(custom_name)
            if not sanitized_name:
                os.remove(filepath)
                return jsonify({'error': 'Policy name contains no valid characters for filename'}), 400

            baseline_filename = os.path.basename(filepath)
            session.update(
                session_id=session_id,
                baseline_filename=baseline_filename,
                custom_name=custom_name,
                sanitized_name=sanitized_name,
                custom_description=custom_description,
                decisions={},
            )
            session.permanent = True

            SessionService(current_app.config['DRAFT_FOLDER']).save_draft(
                session_id,
                SessionService.serialize_session_data(
                    baseline_filename, custom_name, sanitized_name, custom_description, {}
                ),
            )
            return jsonify({
                'success': True,
                'redirect': url_for('review.review_page'),
                'recovery_url': url_for('upload.recover_draft', session_id=session_id),
            })
        except Exception:
            if os.path.exists(filepath):
                os.remove(filepath)
            raise
    except Exception:
        logger.exception("Unable to upload SCA file")
        return jsonify({'error': 'Unable to process SCA file.'}), 500


@upload_bp.route('/recover/<session_id>')
def recover_draft(session_id: str) -> tuple[Response, Literal[404]] | tuple[Response, Literal[410]] | wResponse | tuple[Response, Literal[400]]:
    service = SessionService(current_app.config['DRAFT_FOLDER'])
    data = service.load_draft(session_id)
    if not data:
        return jsonify({'error': 'Draft not found'}), 404
    try:
        filename = str(data['baseline_filename'])
        path = contained_path(current_app.config['UPLOAD_FOLDER'], filename)
        if not path.is_file():
            return jsonify({'error': 'Draft baseline is no longer available'}), 410
        session.clear()
        session.update(
            session_id=session_id,
            baseline_filename=filename,
            custom_name=data['custom_name'],
            sanitized_name=data['sanitized_name'],
            custom_description=data['custom_description'],
            decisions=data.get('decisions', {}),
        )
        session.permanent = True
        return redirect(url_for('review.review_page'))
    except (KeyError, TypeError, ValueError):
        logger.warning("Invalid draft data for %s", session_id, exc_info=True)
        return jsonify({'error': 'Draft is invalid'}), 400


@upload_bp.route('/api/drafts/<session_id>', methods=['DELETE'])
def delete_draft(session_id: str) -> Response | tuple[Response, Literal[400]] | tuple[Response, Literal[404]] | tuple[Response, Literal[500]]:
    service = SessionService(current_app.config['DRAFT_FOLDER'])
    try:
        session_id = service.validate_session_id(session_id)
    except ValueError:
        return jsonify({'error': 'Invalid draft identifier'}), 400

    data = service.load_draft(session_id)
    if data is None:
        return jsonify({'error': 'Draft not found'}), 404

    try:
        baseline_filename = data.get('baseline_filename')
        if isinstance(baseline_filename, str):
            contained_path(current_app.config['UPLOAD_FOLDER'], baseline_filename).unlink(missing_ok=True)
        if not service.delete_draft(session_id):
            return jsonify({'error': 'Unable to delete draft'}), 500
        if session.get('session_id') == session_id:
            session.clear()
        return jsonify({'success': True, 'session_id': session_id})
    except (TypeError, ValueError):
        logger.warning('Invalid persisted path for draft %s', session_id, exc_info=True)
        return jsonify({'error': 'Draft is invalid'}), 400
    except Exception:
        logger.exception('Unable to delete draft %s', session_id)
        return jsonify({'error': 'Unable to delete draft'}), 500
