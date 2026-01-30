"""Review routes - Review interface and AJAX endpoints."""
from flask import Blueprint, render_template, request, session, jsonify, current_app

from services.sca_service import SCAService
from services.session_service import SessionService


review_bp = Blueprint('review', __name__)


@review_bp.route('/review')
def review_page():
    """Main review interface."""
    # Check if session is initialized
    if 'session_id' not in session or 'baseline_path' not in session:
        return jsonify({'error': 'No active session. Please upload a file first.'}), 400
    
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
    except Exception as e:
        return jsonify({'error': f'Error loading review page: {str(e)}'}), 500


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
        check['excluded'] = check_decision.get('excluded', False)
        check['justification'] = check_decision.get('justification', '')
        
        return jsonify(check)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@review_bp.route('/api/decision', methods=['POST'])
def save_decision():
    """Save exclusion decision (AJAX)."""
    if 'session_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    try:
        data = request.get_json()
        check_id = data.get('check_id')
        excluded = data.get('excluded', False)
        justification = data.get('justification', '').strip()
        
        # Validate
        if excluded and (not justification or len(justification) < 10):
            return jsonify({'error': 'Justification must be at least 10 characters when excluding a check'}), 400
        
        if justification and len(justification) > 1000:
            return jsonify({'error': 'Justification must not exceed 1000 characters'}), 400
        
        # Update session
        decisions = session.get('decisions', {})
        decisions[str(check_id)] = {
            'excluded': excluded,
            'justification': justification
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
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@review_bp.route('/api/stats')
def get_stats():
    """Get current review statistics."""
    if 'baseline_path' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    try:
        guide = SCAService.load_baseline(session['baseline_path'])
        checks = SCAService.get_checks(guide)
        decisions = session.get('decisions', {})
        
        total = len(checks)
        excluded = sum(1 for d in decisions.values() if d.get('excluded', False))
        included = total - excluded
        reviewed = len(decisions)
        
        return jsonify({
            'total': total,
            'included': included,
            'excluded': excluded,
            'reviewed': reviewed
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
