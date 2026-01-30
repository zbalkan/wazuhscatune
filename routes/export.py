"""Export routes - Export and download functionality."""
import os
from flask import Blueprint, render_template, request, session, jsonify, send_file, current_app

from services.sca_service import SCAService
from services.export_service import ExportService
from services.session_service import SessionService
from internal.sca import SCA, Check


export_bp = Blueprint('export', __name__)


@export_bp.route('/approval')
def approval_page():
    """Final approval page."""
    if 'session_id' not in session or 'baseline_path' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    try:
        guide = SCAService.load_baseline(session['baseline_path'])
        checks = SCAService.get_checks(guide)
        decisions = session.get('decisions', {})
        
        # Calculate statistics
        total = len(checks)
        excluded_checks = []
        
        for check in checks:
            check_id = str(check['id'])
            if check_id in decisions and decisions[check_id].get('excluded', False):
                excluded_checks.append({
                    'id': check['id'],
                    'title': check['title'],
                    'justification': decisions[check_id].get('justification', '')
                })
        
        excluded = len(excluded_checks)
        included = total - excluded
        
        return render_template('approval.html',
                             custom_name=session.get('custom_name'),
                             custom_description=session.get('custom_description'),
                             total=total,
                             included=included,
                             excluded=excluded,
                             excluded_checks=excluded_checks)
    except Exception as e:
        return jsonify({'error': f'Error loading approval page: {str(e)}'}), 500


@export_bp.route('/api/export', methods=['POST'])
def export_files():
    """Generate export files."""
    if 'session_id' not in session or 'baseline_path' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    try:
        # Load guide
        guide = SCAService.load_baseline(session['baseline_path'])
        sca = SCA.from_dict(guide.__sca_yml__)
        
        # Get decisions
        decisions = session.get('decisions', {})
        
        # Validate at least one check remains included
        total_checks = len(sca.checks)
        excluded_count = sum(1 for d in decisions.values() if d.get('excluded', False))
        
        if excluded_count >= total_checks:
            return jsonify({'error': 'At least one check must remain included'}), 400
        
        # Create loosening object
        custom_name = session.get('custom_name')
        custom_description = session.get('custom_description')
        custom_id = custom_name.lower().replace(' ', '_').replace('-', '_').replace('.', '_')
        custom_id = custom_id.replace('___', '_').replace('__', '_')
        
        full_description = f"{custom_description} (Based on {sca.policy.name})"
        loosening = SCAService.create_loosening(custom_name, custom_id, full_description)
        
        # Add decisions to loosening
        for check in sca.checks:
            check_id = str(check.id)
            if check_id in decisions and decisions[check_id].get('excluded', False):
                justification = decisions[check_id].get('justification', '')
                SCAService.add_decision(loosening, check, justification)
        
        # Generate files
        base_filename = custom_id
        custom_sca_path, loosening_yml_path, loosening_md_path = ExportService.generate_files(
            guide, loosening, base_filename
        )
        
        # Create ZIP archive
        files = [custom_sca_path, loosening_yml_path, loosening_md_path]
        zip_filename = f"{custom_id}_export.zip"
        zip_path = ExportService.create_zip_archive(files, zip_filename)
        
        # Store ZIP path in session for download
        session['export_zip_path'] = zip_path
        session['export_zip_filename'] = zip_filename
        session.modified = True
        
        return jsonify({
            'success': True,
            'download_url': '/download'
        })
        
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


@export_bp.route('/download')
def download_file():
    """Download ZIP file."""
    if 'export_zip_path' not in session:
        return jsonify({'error': 'No file to download'}), 400
    
    zip_path = session['export_zip_path']
    zip_filename = session.get('export_zip_filename', 'export.zip')
    
    if not os.path.exists(zip_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(zip_path, as_attachment=True, download_name=zip_filename)


@export_bp.route('/api/cleanup', methods=['POST'])
def cleanup_session():
    """Cleanup session files."""
    try:
        session_id = session.get('session_id')
        baseline_path = session.get('baseline_path')
        export_zip_path = session.get('export_zip_path')
        
        # Clean up uploaded file
        if baseline_path and os.path.exists(baseline_path):
            os.remove(baseline_path)
        
        # Clean up export ZIP and its directory
        if export_zip_path:
            ExportService.cleanup_temp_files(export_zip_path)
            # Also remove the temp directory
            temp_dir = os.path.dirname(export_zip_path)
            if os.path.exists(temp_dir):
                ExportService.cleanup_temp_files(temp_dir)
        
        # Clean up draft
        if session_id:
            session_service = SessionService(current_app.config['DRAFT_FOLDER'])
            session_service.delete_draft(session_id)
        
        # Clear session
        session.clear()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
