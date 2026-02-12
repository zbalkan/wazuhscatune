"""Upload routes - File upload and validation."""
import os
import uuid
import re
from flask import Blueprint, render_template, request, session, url_for, jsonify, current_app
from werkzeug.utils import secure_filename

from services.sca_service import SCAService
from services.session_service import SessionService


upload_bp = Blueprint('upload', __name__)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def sanitize_policy_name(name):
    """
    Sanitize policy name for use as filename.
    - Convert to lowercase
    - Remove problematic punctuation
    - Replace spaces with underscores
    - Remove leading/trailing underscores
    
    Example: "Company Windows 11 Hardening Policy" -> "company_windows_11_hardening_policy"
    """
    if not name:
        return ''
    
    # Convert to lowercase
    sanitized = name.lower()
    
    # Keep only alphanumeric, spaces, hyphens, and underscores
    sanitized = re.sub(r'[^a-z0-9\s\-_]', '', sanitized)
    
    # Replace multiple spaces/hyphens with single space
    sanitized = re.sub(r'[\s\-]+', ' ', sanitized)
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    
    # Remove leading/trailing underscores
    sanitized = re.sub(r'^_+|_+$', '', sanitized)
    
    return sanitized


@upload_bp.route('/')
def index():
    """Landing page with upload form."""
    return render_template('index.html')


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload, validation, and session initialization."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only .yml and .yaml files are allowed'}), 400
        
        # Get custom policy details
        custom_name = request.form.get('custom_name', '').strip()
        custom_description = request.form.get('custom_description', '').strip()
        
        # Validate inputs
        if not custom_name or len(custom_name) < 15 or len(custom_name) > 100:
            return jsonify({'error': 'Policy name must be between 15 and 100 characters'}), 400
        
        if not custom_description or len(custom_description) < 50 or len(custom_description) > 500:
            return jsonify({'error': 'Policy description must be between 50 and 500 characters'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        session_id = str(uuid.uuid4())
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
        
        try:
            file.save(filepath)
            
            # Validate SCA file
            is_valid, error_msg = SCAService.validate_sca_file(filepath)
            if not is_valid:
                os.remove(filepath)
                return jsonify({'error': f'Invalid SCA file: {error_msg}'}), 400
            
            # Sanitize policy name for filename
            sanitized_name = sanitize_policy_name(custom_name)
            if not sanitized_name:
                os.remove(filepath)
                return jsonify({'error': 'Policy name contains no valid characters for filename'}), 400
            
            # Initialize session
            session['session_id'] = session_id
            session['baseline_path'] = filepath
            session['custom_name'] = custom_name
            session['sanitized_name'] = sanitized_name  # Store sanitized name for file generation
            session['custom_description'] = custom_description
            session['decisions'] = {}
            session.permanent = True
            
            # Save draft
            session_service = SessionService(current_app.config['DRAFT_FOLDER'])
            session_data = SessionService.serialize_session_data(
                filepath, custom_name, custom_description, {}
            )
            session_service.save_draft(session_id, session_data)
            
            return jsonify({
                'success': True,
                'redirect': url_for('review.review_page')
            })
        except Exception as e:
            # Clean up uploaded file on error
            if os.path.exists(filepath):
                os.remove(filepath)
            raise
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@upload_bp.route('/validate', methods=['POST'])
def validate_file():
    """AJAX endpoint for file validation."""
    try:
        if 'file' not in request.files:
            return jsonify({'valid': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'valid': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'valid': False, 'error': 'Invalid file type'}), 400
        
        # Save to temporary location for validation
        filename = secure_filename(file.filename)
        validation_id = str(uuid.uuid4())
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"validate_{validation_id}_{filename}")
        file.save(temp_path)
        
        # Validate
        is_valid, error_msg = SCAService.validate_sca_file(temp_path)
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if is_valid:
            return jsonify({'valid': True})
        else:
            return jsonify({'valid': False, 'error': error_msg})
            
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500
