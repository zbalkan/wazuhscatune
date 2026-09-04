"""Export routes - Export and download functionality."""
import os
import logging
from flask import Blueprint, render_template, session, jsonify, send_file, current_app, redirect, url_for

from services.sca_service import SCAService
from services.export_service import ExportService
from services.session_service import SessionService
from internal.sca import SCA


export_bp = Blueprint('export', __name__)
logger = logging.getLogger(__name__)


@export_bp.route('/approval')
def approval_page():
    """Final approval page."""
    if 'session_id' not in session or 'baseline_path' not in session:
        return redirect(url_for('upload.index'))

    try:
        guide = SCAService.load_baseline(session['baseline_path'])
        checks = SCAService.get_checks(guide)
        decisions = session.get('decisions', {})

        # Calculate statistics
        total = len(checks)
        excluded_checks = []

        for check in checks:
            check_id = str(check['id'])
            if check_id in decisions and decisions[check_id].get('decision') == 'exception':
                excluded_checks.append({
                    'id': check['id'],
                    'title': check['title'],
                    'justification': decisions[check_id].get('justification', '')
                })

        stats = SCAService.calculate_stats(guide, decisions)

        return render_template('approval.html',
                             custom_name=session.get('custom_name'),
                             custom_description=session.get('custom_description'),
                             total=total,
                             stats=stats,
                             excluded_checks=excluded_checks)
    except Exception:
        logger.exception("Unable to load approval page")
        return jsonify({'error': 'Unable to process SCA file.'}), 500


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
        baseline_ids = {check.id for check in sca.checks}
        excluded_ids = set()
        for raw_id, decision in decisions.items():
            try:
                check_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if (check_id in baseline_ids and isinstance(decision, dict)
                    and decision.get('decision') == 'exception'
                    and isinstance(decision.get('justification'), str)
                    and len(decision['justification'].strip()) >= 10):
                excluded_ids.add(check_id)

        if excluded_ids == baseline_ids:
            return jsonify({'error': 'At least one check must remain included'}), 400

        # Create loosening object
        custom_name = session.get('custom_name')
        custom_description = session.get('custom_description')
        # Use the sanitized name stored during upload
        sanitized_name = session.get('sanitized_name')
        if not sanitized_name:
            # Fallback to old sanitization if not in session (backward compatibility)
            sanitized_name = custom_name.lower().replace(' ', '_').replace('-', '_').replace('.', '_')
            sanitized_name = sanitized_name.replace('___', '_').replace('__', '_')

        full_description = f"{custom_description} (Based on {sca.policy.name})"
        loosening = SCAService.create_loosening(custom_name, sanitized_name, full_description)

        # Add decisions to loosening
        for check in sca.checks:
            check_id = str(check.id)
            if check.id in excluded_ids:
                justification = decisions[check_id].get('justification', '')
                SCAService.add_decision(loosening, check, justification)

        # Generate files using sanitized name
        base_filename = sanitized_name
        custom_sca_path, loosening_yml_path, loosening_md_path, temp_dir = ExportService.generate_files(
            guide, loosening, base_filename
        )

        # Create ZIP archive
        files = [custom_sca_path, loosening_yml_path, loosening_md_path]
        zip_filename = f"{sanitized_name}_export.zip"
        zip_path = ExportService.create_zip_archive(files, zip_filename)

        # Store paths in session for download and cleanup
        session['export_zip_path'] = zip_path
        session['export_zip_filename'] = zip_filename
        session['export_temp_dir'] = temp_dir
        session.modified = True

        return jsonify({
            'success': True,
            'download_url': '/download'
        })

    except Exception:
        logger.exception("Unable to generate export")
        return jsonify({'error': 'Unable to generate export.'}), 500


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
        export_temp_dir = session.get('export_temp_dir')

        # Clean up uploaded file
        if baseline_path and os.path.exists(baseline_path):
            os.remove(baseline_path)

        # Clean up export ZIP and its directory
        if export_zip_path:
            ExportService.cleanup_temp_files(export_zip_path)
            # Also remove the ZIP temp directory
            zip_temp_dir = os.path.dirname(export_zip_path)
            if os.path.exists(zip_temp_dir):
                ExportService.cleanup_temp_files(zip_temp_dir)

        # Clean up generation temp directory
        if export_temp_dir and os.path.exists(export_temp_dir):
            ExportService.cleanup_temp_files(export_temp_dir)

        # Clean up draft
        if session_id:
            session_service = SessionService(current_app.config['DRAFT_FOLDER'])
            session_service.delete_draft(session_id)

        # Clear session
        session.clear()

        return jsonify({'success': True})

    except Exception:
        logger.exception("Unable to clean up session")
        return jsonify({'error': 'Unable to clean up session.'}), 500
