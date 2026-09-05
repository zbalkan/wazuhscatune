"""Review routes - Review interface and AJAX endpoints."""
import logging
from flask import Blueprint, render_template, request, session, jsonify, current_app, redirect, url_for

from sca.services.sca_service import SCAService
from sca.services.session_service import SessionService
from sca.services.session_service import contained_path
from sca.internal.review import ReviewDecision, normalize_decisions


review_bp = Blueprint('review', __name__)
logger = logging.getLogger(__name__)


def _baseline_path() -> str:
    return str(contained_path(current_app.config['UPLOAD_FOLDER'],
                              session['baseline_filename']))


@review_bp.route('/review')
def review_page():
    """Main review interface."""
    # Check if session is initialized
    if 'session_id' not in session or 'baseline_filename' not in session:
        return redirect(url_for('upload.index'))

    try:
        # Load guide
        guide = SCAService.load_baseline(_baseline_path())

        # Get summary and checks
        summary = SCAService.get_sca_summary(guide)
        checks = SCAService.get_checks(guide)
        checks_client = [dict(check, id=str(check['id'])) for check in checks]

        # Get decisions from session
        decisions = session.get('decisions', {})

        baseline_ids = {check['id'] for check in checks}
        decisions_int = {str(key): value.to_session() for key, value in
                         normalize_decisions(decisions, baseline_ids).items()}
        stats = SCAService.calculate_stats(guide, decisions)

        return render_template('review.html',
                             policy_name=session.get('custom_name'),
                             summary=summary,
                             checks=checks, checks_client=checks_client,
                             decisions=decisions_int, stats=stats)
    except Exception:
        logger.exception("Unable to load review page")
        return jsonify({'error': 'Unable to process SCA file.'}), 500


@review_bp.route('/api/check/<int:check_id>')
def get_check(check_id):
    """Get specific check details (AJAX)."""
    if 'baseline_filename' not in session:
        return jsonify({'error': 'No active session'}), 400

    try:
        guide = SCAService.load_baseline(_baseline_path())
        check = SCAService.get_check_by_id(guide, check_id)

        if check is None:
            return jsonify({'error': 'Check not found'}), 404

        # Add decision info if exists
        decisions = session.get('decisions', {})
        check_decision = decisions.get(str(check_id), {})
        if not isinstance(check_decision, dict):
            check_decision = {}
        check['decision'] = check_decision.get('decision', 'unreviewed')
        check['justification'] = check_decision.get('justification', '')

        return jsonify(check)
    except Exception:
        logger.exception("Unable to load check %s", check_id)
        return jsonify({'error': 'Unable to process SCA file.'}), 500


@review_bp.route('/api/decision', methods=['POST'])
def save_decision():
    """Save exclusion decision (AJAX)."""
    if 'session_id' not in session:
        return jsonify({'error': 'No active session'}), 400

    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid or missing JSON body'}), 400

        check_id_raw = data.get('check_id')
        if check_id_raw is None:
            return jsonify({'error': 'Missing required field: check_id'}), 400
        if isinstance(check_id_raw, bool) or not isinstance(check_id_raw, (str, int)):
            return jsonify({'error': 'Field check_id must be an integer string'}), 400
        try:
            check_id = int(check_id_raw)
        except ValueError:
            return jsonify({'error': 'Field check_id must be an integer string'}), 400
        if str(check_id) != str(check_id_raw):
            return jsonify({'error': 'Field check_id must be an integer string'}), 400

        guide = SCAService.load_baseline(_baseline_path())
        if SCAService.get_check_by_id(guide, check_id) is None:
            return jsonify({'error': 'Unknown check ID'}), 404
        try:
            normalized = ReviewDecision.create(
                check_id, data.get('decision'), data.get('justification', ''))
        except ValueError as error:
            return jsonify({'error': str(error)}), 400

        # Update session
        decisions = session.get('decisions', {})
        decisions[str(check_id)] = normalized.to_session()
        session['decisions'] = decisions
        session.modified = True

        # Save draft
        session_service = SessionService(current_app.config['DRAFT_FOLDER'])
        session_data = SessionService.serialize_session_data(
            session['baseline_filename'],
            session['custom_name'],
            session['sanitized_name'],
            session['custom_description'],
            decisions
        )
        session_service.save_draft(session['session_id'], session_data)

        return jsonify({
            'success': True, 'check_id': str(check_id),
            'decision': decisions[str(check_id)],
            'stats': SCAService.calculate_stats(guide, decisions),
        })

    except Exception:
        logger.exception("Unable to save review decision")
        return jsonify({'error': 'Unable to save review state.'}), 500


@review_bp.route('/api/save-draft', methods=['POST'])
def manual_save_draft():
    """Manually save draft."""
    if 'session_id' not in session:
        return jsonify({'error': 'No active session'}), 400

    try:
        session_service = SessionService(current_app.config['DRAFT_FOLDER'])
        session_data = SessionService.serialize_session_data(
            session['baseline_filename'],
            session['custom_name'],
            session['sanitized_name'],
            session['custom_description'],
            session.get('decisions', {})
        )
        success = session_service.save_draft(session['session_id'], session_data)

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to save draft'}), 500

    except Exception:
        logger.exception("Unable to save draft")
        return jsonify({'error': 'Unable to save review state.'}), 500


@review_bp.route('/api/stats')
def get_stats():
    """Get current review statistics."""
    if 'baseline_filename' not in session:
        return jsonify({'error': 'No active session'}), 400

    try:
        guide = SCAService.load_baseline(_baseline_path())
        decisions = session.get('decisions', {})

        return jsonify(SCAService.calculate_stats(guide, decisions))

    except Exception:
        logger.exception("Unable to calculate review statistics")
        return jsonify({'error': 'Unable to process SCA file.'}), 500
