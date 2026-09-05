"""Draft lifecycle routes."""
import logging
from pathlib import Path
from typing import Literal

from flask import Blueprint, Response, current_app, jsonify, session

from sca.services.session_service import SessionService, contained_path


drafts_bp = Blueprint('drafts', __name__)
logger = logging.getLogger(__name__)


@drafts_bp.route('/api/drafts/<session_id>', methods=['DELETE'])
def delete_draft(session_id: str) -> Response | tuple[Response, Literal[400]] | tuple[Response, Literal[404]] | tuple[Response, Literal[500]]:
    """Delete one persisted draft and its uploaded baseline."""
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
            baseline_path: Path = contained_path(
                current_app.config['UPLOAD_FOLDER'], baseline_filename)
            baseline_path.unlink(missing_ok=True)

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
