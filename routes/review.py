"""Review routes - Review interface and AJAX endpoints."""
import logging
from flask import Blueprint, render_template, request, session, jsonify, current_app, redirect, url_for

from services.sca_service import SCAService
from services.session_service import SessionService


review_bp = Blueprint('review', __name__)
logger = logging.getLogger(__name__)


@review_bp.route('/review')
def review_page():
    """Main review interface."""
    # Check if session is initialized
    if 'session_id' not in session or 'baseline_path' not in session:
        return redirect(url_for('upload.index'))
    
    try:
        # Load guide
        guide = SCAService.load_baseline(session['baseline_path'])
        
        # Get summary and checks
        summary = SCAService.get_sca_summary(guide)
        checks = SCAService.get_checks(guide)
        
        # Get decisions from session
        decisions = session.get('decisions', {})
        
        # Convert string keys back to int for decisions
        decisions_int = {int(k): v for k, v in decisions.items()}
        
        return render_template('review.html',
                             policy_name=session.get('custom_name'),
                             summary=summary,
                             checks=checks,
                             decisions=decisions_int)
    except Exception:
        logger.exception("Unable to load review page")
        return jsonify({'error': 'Unable to process SCA file.'}), 500


@review_bp.route('/api/check/<int:check_id>')
def get_check(check_id):
    """Get specific check details (AJAX)."""
    if 'baseline_path' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    try:
        guide = SCAService.load_baseline(session['baseline_path'])
        check = SCAService.get_check_by_id(guide, check_id)
        
        if check is None:
            return jsonify({'error': 'Check not found'}), 404
        
        # Add decision info if exists
        decisions = session.get('decisions', {})
        check_decision = decisions.get(str(check_id), {})
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

        check_id = data.get('check_id')
        if check_id is None:
            return jsonify({'error': 'Missing required field: check_id'}), 400
        if type(check_id) is not int:
            return jsonify({'error': 'Field check_id must be an integer'}), 400

        decision = data.get('decision')
        if decision not in ('accepted', 'exception'):
            return jsonify({'error': "Field decision must be 'accepted' or 'exception'"}), 400
        raw_justification = data.get('justification', '')
        if not isinstance(raw_justification, str):
            return jsonify({'error': 'Field justification must be a string'}), 400
        justification = raw_justification.strip()

        guide = SCAService.load_baseline(session['baseline_path'])
        if SCAService.get_check_by_id(guide, check_id) is None:
            return jsonify({'error': 'Unknown check ID'}), 404
        
        # Validate
        if decision == 'exception' and len(justification) < 10:
            return jsonify({'error': 'Justification must be at least 10 characters for an exception'}), 400
        
        if justification and len(justification) > 1000:
            return jsonify({'error': 'Justification must not exceed 1000 characters'}), 400
        
        # Update session
        decisions = session.get('decisions', {})
        decisions[str(check_id)] = {
            'decision': decision,
            **({'justification': justification} if decision == 'exception' else {})
        }
        session['decisions'] = decisions
        session.modified = True
        
        # Save draft
        session_service = SessionService(current_app.config['DRAFT_FOLDER'])
        session_data = SessionService.serialize_session_data(
            session['baseline_path'],
            session['custom_name'],
            session['custom_description'],
            decisions
        )
        session_service.save_draft(session['session_id'], session_data)
        
        return jsonify({
            'success': True, 'check_id': check_id,
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
            session['baseline_path'],
            session['custom_name'],
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
    if 'baseline_path' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    try:
        guide = SCAService.load_baseline(session['baseline_path'])
        checks = SCAService.get_checks(guide)
        decisions = session.get('decisions', {})
        
        return jsonify(SCAService.calculate_stats(guide, decisions))
        
    except Exception:
        logger.exception("Unable to calculate review statistics")
        return jsonify({'error': 'Unable to process SCA file.'}), 500
