"""Export routes."""
import logging
import os
from typing import Literal

from flask import Blueprint, current_app, jsonify, redirect, render_template, send_file, session, url_for
from flask.wrappers import Response
from werkzeug import Response as wResponse

from sca.internal.guide import Guide
from sca.internal.review import DecisionType, ReviewDecision, normalize_decisions
from sca.routes.upload import sanitize_policy_name
from sca.services.export_service import cleanup_export, export_policy
from sca.services.sca_service import add_exception, calculate_stats, create_tailoring, get_checks
from sca.services.session_service import SessionService, contained_path, validate_contained

export_bp = Blueprint('export', __name__)
logger = logging.getLogger(__name__)


def _baseline_path() -> str:
    return str(contained_path(current_app.config['UPLOAD_FOLDER'], session['baseline_filename']))


def _review_complete(guide: Guide, decisions: object) -> bool:
    baseline_ids = {check.id for check in guide.sca.checks}
    normalized = normalize_decisions(decisions, baseline_ids)
    return set(normalized) == baseline_ids


@export_bp.route('/approval')
def approval_page() -> wResponse | str:
    if 'session_id' not in session or 'baseline_filename' not in session:
        return redirect(url_for('upload.index'))
    try:
        guide = Guide(_baseline_path())
        checks = get_checks(guide)
        decisions = session.get('decisions', {})
        if not _review_complete(guide, decisions):
            return redirect(url_for('review.review_page'))

        normalized = normalize_decisions(decisions, {check['id'] for check in checks})
        excluded_checks = [
            {
                'id': check['id'],
                'title': check['title'],
                'justification': normalized[check['id']].justification or '',
            }
            for check in checks
            if normalized[check['id']].decision is DecisionType.EXCEPTION
        ]
        return render_template(
            'approval.html',
            custom_name=session.get('custom_name'),
            custom_description=session.get('custom_description'),
            stats=calculate_stats(guide, decisions),
            excluded_checks=excluded_checks,
        )
    except Exception:
        logger.exception("Unable to load approval page")
        raise


@export_bp.route('/api/export', methods=['POST'])
def export_files() -> tuple[Response, Literal[400]] | Response | tuple[Response, Literal[500]]:
    if 'session_id' not in session or 'baseline_filename' not in session:
        return jsonify({'error': 'No active session'}), 400

    try:
        guide = Guide(_baseline_path())
        decisions = session.get('decisions', {})
        baseline_ids = {check.id for check in guide.sca.checks}
        try:
            normalized: dict[int, ReviewDecision] = normalize_decisions(
                decisions, baseline_ids, strict=True)
        except ValueError:
            return jsonify({'error': 'Review state is invalid; review the affected checks again.'}), 400

        if set(normalized) != baseline_ids:
            return jsonify({'error': 'All checks must be reviewed before export.'}), 400

        excluded_ids = {
            check_id for check_id, value in normalized.items()
            if value.decision is DecisionType.EXCEPTION
        }
        if excluded_ids == baseline_ids:
            return jsonify({'error': 'At least one check must remain included'}), 400

        custom_name = session.get('custom_name')
        custom_description = session.get('custom_description')
        sanitized_name = session.get('sanitized_name')
        if not isinstance(custom_name, str) or not custom_name.strip():
            return jsonify({'error': 'Review session is invalid; start a new review.'}), 400
        if not isinstance(custom_description, str) or not custom_description.strip():
            return jsonify({'error': 'Review session is invalid; start a new review.'}), 400
        if (not isinstance(sanitized_name, str) or not sanitized_name or
                sanitize_policy_name(sanitized_name) != sanitized_name):
            sanitized_name = sanitize_policy_name(custom_name)
        if not sanitized_name:
            return jsonify({'error': 'Review session has no valid export filename; start a new review.'}), 400

        tailoring = create_tailoring(
            custom_name,
            sanitized_name,
            f"{custom_description} (Based on {guide.sca.policy.name})",
        )
        for check in guide.sca.checks:
            if check.id in excluded_ids:
                add_exception(tailoring, check, normalized[check.id].justification or '')

        previous_path = None
        previous = session.get('export_zip_path')
        if isinstance(previous, str):
            try:
                previous_path = str(validate_contained(
                    current_app.config['EXPORT_FOLDER'], previous))
            except ValueError:
                pass

        zip_path = export_policy(
            guide, tailoring, sanitized_name, current_app.config['EXPORT_FOLDER'])
        session['export_zip_path'] = zip_path
        session['export_zip_filename'] = f'{sanitized_name}_export.zip'
        session.modified = True

        if previous_path is not None:
            cleanup_export(previous_path)

        return jsonify({'success': True, 'download_url': '/download'})
    except Exception:
        logger.exception("Unable to generate export")
        return jsonify({'error': 'Unable to generate export.'}), 500


@export_bp.route('/download')
def download_file() -> tuple[Response, Literal[400]] | tuple[Response, Literal[404]] | Response:
    if 'export_zip_path' not in session:
        return jsonify({'error': 'No file to download'}), 400
    try:
        zip_path = str(validate_contained(
            current_app.config['EXPORT_FOLDER'], session['export_zip_path']))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid download path'}), 400
    if not os.path.exists(zip_path):
        return jsonify({'error': 'File not found'}), 404
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=session.get('export_zip_filename', 'export.zip'),
    )


@export_bp.route('/api/cleanup', methods=['POST'])
def cleanup_session() -> Response | tuple[Response, Literal[500]]:
    try:
        baseline_filename = session.get('baseline_filename')
        if isinstance(baseline_filename, str):
            contained_path(current_app.config['UPLOAD_FOLDER'], baseline_filename).unlink(missing_ok=True)

        export_zip_path = session.get('export_zip_path')
        if isinstance(export_zip_path, str):
            cleanup_export(str(validate_contained(
                current_app.config['EXPORT_FOLDER'], export_zip_path)))

        session_id = session.get('session_id')
        if isinstance(session_id, str):
            SessionService(current_app.config['DRAFT_FOLDER']).delete_draft(session_id)

        session.clear()
        return jsonify({'success': True})
    except Exception:
        logger.exception("Unable to clean up session")
        return jsonify({'error': 'Unable to clean up session.'}), 500
