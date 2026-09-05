"""Export routes - Export and download functionality."""
import logging
import os
from typing import Any, Literal

from flask import Blueprint, current_app, jsonify, redirect, render_template, send_file, session, url_for
from flask.wrappers import Response
from werkzeug import Response as wResponse

from sca.internal.guide import Guide
from sca.internal.loosening import Tailoring
from sca.internal.review import DecisionType, ReviewDecision, normalize_decisions
from sca.routes.upload import sanitize_policy_name
from sca.services.export_service import ExportService
from sca.services.sca_service import SCAService
from sca.services.session_service import SessionService, contained_path, validate_contained

export_bp = Blueprint('export', __name__)
logger: logging.Logger = logging.getLogger(__name__)


def _baseline_path() -> str:
    return str(contained_path(current_app.config['UPLOAD_FOLDER'],
                              session['baseline_filename']))


@export_bp.route('/approval')
def approval_page() -> wResponse | str:
    """Final approval page."""
    if 'session_id' not in session or 'baseline_filename' not in session:
        return redirect(url_for('upload.index'))

    try:
        guide: Guide = SCAService.load_baseline(_baseline_path())
        checks: list[dict[str, Any]] = SCAService.get_checks(guide)
        decisions = session.get('decisions', {})

        # Calculate statistics
        total: int = len(checks)
        excluded_checks = []

        normalized: dict[int, ReviewDecision] = normalize_decisions(decisions, {check['id'] for check in checks})
        for check in checks:
            check_decision = normalized.get(check['id'])
            if check_decision and check_decision.decision is DecisionType.EXCEPTION:
                excluded_checks.append({
                    'id': check['id'],
                    'title': check['title'],
                    'justification': check_decision.justification or ''
                })

        stats: dict[str, Any] = SCAService.calculate_stats(guide, decisions)

        return render_template('approval.html',
                               custom_name=session.get('custom_name'),
                               custom_description=session.get('custom_description'),
                               total=total,
                               stats=stats,
                               excluded_checks=excluded_checks)
    except Exception:
        logger.exception("Unable to load approval page")
        raise


@export_bp.route('/api/export', methods=['POST'])
def export_files() -> tuple[Response, Literal[400]] | Response | tuple[Response, Literal[500]]:
    """Generate export files."""
    if 'session_id' not in session or 'baseline_filename' not in session:
        return jsonify({'error': 'No active session'}), 400

    try:
        # Load guide
        guide: Guide = SCAService.load_baseline(_baseline_path())
        sca = guide.sca

        # Get decisions
        decisions = session.get('decisions', {})

        # Validate at least one check remains included
        baseline_ids: set[int] = {check.id for check in sca.checks}
        try:
            normalized: dict[int, ReviewDecision] = normalize_decisions(decisions, baseline_ids, strict=True)
        except ValueError:
            return jsonify({'error': 'Review state is invalid; review the affected checks again.'}), 400
        excluded_ids: set[int] = {check_id for check_id, value in normalized.items()
                                  if value.decision is DecisionType.EXCEPTION}

        if excluded_ids == baseline_ids:
            return jsonify({'error': 'At least one check must remain included'}), 400

        # Create tailoring record
        custom_name = session.get('custom_name')
        custom_description = session.get('custom_description')
        sanitized_name = str(session.get('sanitized_name'))
        if not sanitized_name:
            # Legacy drafts may not have stored the sanitized filename.
            if not isinstance(custom_name, str) or not custom_name.strip():
                return jsonify({'error': 'Review session is invalid; start a new review.'}), 400
            sanitized_name = sanitize_policy_name(custom_name)
            if not sanitized_name:
                return jsonify({'error': 'Review session has no valid export filename; start a new review.'}), 400

        full_description: str = f"{custom_description} (Based on {sca.policy.name})"
        tailoring: Tailoring = SCAService.create_tailoring(custom_name, sanitized_name, full_description)  # type: ignore

        # Add decisions to loosening
        for check in sca.checks:
            if check.id in excluded_ids:
                justification: str = normalized[check.id].justification or ''
                SCAService.add_exception(tailoring, check, justification)

        # Generate files using sanitized name
        base_filename: str = sanitized_name
        custom_sca_path, loosening_yml_path, loosening_md_path, temp_dir = ExportService.generate_files(
            guide, tailoring, base_filename, current_app.config['EXPORT_FOLDER']
        )

        # Create ZIP archive
        files: list[str] = [custom_sca_path, loosening_yml_path, loosening_md_path]
        zip_filename: str = f"{sanitized_name}_export.zip"
        zip_path: str = ExportService.create_zip_archive(
            files, zip_filename, current_app.config['EXPORT_FOLDER'])

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
def download_file() -> tuple[Response, Literal[400]] | tuple[Response, Literal[404]] | Response:
    """Download ZIP file."""
    if 'export_zip_path' not in session:
        return jsonify({'error': 'No file to download'}), 400

    try:
        zip_path = str(validate_contained(current_app.config['EXPORT_FOLDER'],
                                          session['export_zip_path']))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid download path'}), 400
    zip_filename = session.get('export_zip_filename', 'export.zip')

    if not os.path.exists(zip_path):
        return jsonify({'error': 'File not found'}), 404

    return send_file(zip_path, as_attachment=True, download_name=zip_filename)


@export_bp.route('/api/cleanup', methods=['POST'])
def cleanup_session() -> Response | tuple[Response, Literal[500]]:
    """Cleanup session files."""
    try:
        session_id = session.get('session_id')
        baseline_filename = session.get('baseline_filename')
        export_zip_path = session.get('export_zip_path')
        export_temp_dir = session.get('export_temp_dir')

        # Clean up uploaded file
        if baseline_filename:
            contained_path(current_app.config['UPLOAD_FOLDER'], baseline_filename).unlink(missing_ok=True)

        # Clean up export ZIP and its directory
        if export_zip_path:
            export_zip_path = str(validate_contained(
                current_app.config['EXPORT_FOLDER'], export_zip_path))
            ExportService.cleanup_temp_files(export_zip_path)
            # Also remove the ZIP temp directory
            zip_temp_dir: str = os.path.dirname(export_zip_path)
            if os.path.exists(zip_temp_dir):
                ExportService.cleanup_temp_files(zip_temp_dir)

        # Clean up generation temp directory
        if export_temp_dir and os.path.exists(export_temp_dir):
            export_temp_dir = str(validate_contained(
                current_app.config['EXPORT_FOLDER'], export_temp_dir))
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
