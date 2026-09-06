"""Review routes."""
import logging
from typing import Any, Literal

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
from flask.wrappers import Response
from werkzeug import Response as wResponse

from sca.internal.guide import Guide
from sca.internal.review import ReviewDecision, normalize_decisions
from sca.services.sca_service import calculate_stats, get_checks
from sca.services.session_service import SessionService, contained_path

review_bp = Blueprint('review', __name__)
logger = logging.getLogger(__name__)


def _baseline_path() -> str:
    return str(contained_path(current_app.config['UPLOAD_FOLDER'], session['baseline_filename']))


def _save_draft(decisions: dict[str, Any]) -> bool:
    data = SessionService.serialize_session_data(
        session['baseline_filename'],
        session['custom_name'],
        session['sanitized_name'],
        session['custom_description'],
        decisions,
    )
    return SessionService(current_app.config['DRAFT_FOLDER']).save_draft(
        session['session_id'], data)


@review_bp.route('/review')
def review_page() -> wResponse | str:
    if 'session_id' not in session or 'baseline_filename' not in session:
        return redirect(url_for('upload.index'))

    try:
        guide = Guide(_baseline_path())
        checks = get_checks(guide)
        decisions = session.get('decisions', {})
        baseline_ids = {check['id'] for check in checks}
        state_error = None
        try:
            normalized = normalize_decisions(decisions, baseline_ids)
        except ValueError:
            logger.warning("Discarding invalid stored review state", exc_info=True)
            if not _save_draft({}):
                raise RuntimeError("Unable to discard invalid stored review state")
            decisions = {}
            normalized = {}
            session['decisions'] = {}
            session.pop('record_generated_at', None)
            session.modified = True
            state_error = (
                "Stored review state was invalid and has been discarded. "
                "The baseline is unchanged; review it again from the beginning."
            )

        decisions_client = {
            str(key): value.to_session()
            for key, value in normalized.items()
        }
        return render_template(
            'review.html',
            policy_name=session.get('custom_name'),
            checks=checks,
            decisions=decisions_client,
            stats=calculate_stats(guide, decisions),
            state_error=state_error,
        )
    except Exception:
        logger.exception("Unable to load review page")
        raise


@review_bp.route('/api/decision', methods=['POST'])
def save_decision() -> tuple[Response, Literal[400]] | tuple[Response, Literal[404]] | Response | tuple[Response, Literal[500]]:
    if 'session_id' not in session:
        return jsonify({'error': 'No active session'}), 400

    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid or missing JSON body'}), 400

        raw_id = data.get('check_id')
        if isinstance(raw_id, bool) or not isinstance(raw_id, (str, int)):
            return jsonify({'error': 'Field check_id must be an integer string'}), 400
        try:
            check_id = int(raw_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'Field check_id must be an integer string'}), 400
        if str(check_id) != str(raw_id):
            return jsonify({'error': 'Field check_id must be an integer string'}), 400

        guide = Guide(_baseline_path())
        baseline_ids = {check.id for check in guide.sca.checks}
        if check_id not in baseline_ids:
            return jsonify({'error': 'Unknown check ID'}), 404

        try:
            current = normalize_decisions(session.get('decisions', {}), baseline_ids)
            decision = ReviewDecision.create(
                check_id, data.get('decision'), data.get('justification', ''))
        except ValueError as error:
            return jsonify({'error': str(error)}), 400

        decisions = {
            str(key): value.to_session()
            for key, value in current.items()
        }
        decisions[str(check_id)] = decision.to_session()
        if not _save_draft(decisions):
            return jsonify({'error': 'Unable to persist review state.'}), 500

        session['decisions'] = decisions
        session.pop('record_generated_at', None)
        session.modified = True
        return jsonify({
            'success': True,
            'check_id': str(check_id),
            'decision': decisions[str(check_id)],
            'stats': calculate_stats(guide, decisions),
        })
    except Exception:
        logger.exception("Unable to save review decision")
        return jsonify({'error': 'Unable to save review state.'}), 500
