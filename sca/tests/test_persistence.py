import io

from ruamel.yaml import YAML

from sca.app import create_app
from sca.services.session_service import SessionService
from sca.tests.helpers import app_with_session, baseline


def test_decision_is_not_acknowledged_when_draft_write_fails(tmp_path, monkeypatch):
    client = app_with_session(tmp_path)
    monkeypatch.setattr(SessionService, 'save_draft', lambda self, session_id, data: False)

    response = client.post('/api/decision', json={
        'check_id': 1,
        'decision': 'accepted',
    })

    assert response.status_code == 500
    with client.session_transaction() as sess:
        assert sess['decisions'] == {}


def test_upload_fails_when_initial_draft_cannot_be_persisted(tmp_path, monkeypatch):
    class TestConfig:
        TESTING = True
        SECRET_KEY = 'test'
        UPLOAD_FOLDER = str(tmp_path / 'uploads')
        DRAFT_FOLDER = str(tmp_path / 'drafts')
        EXPORT_FOLDER = str(tmp_path / 'exports')
        SESSION_FILE_DIR = str(tmp_path / 'sessions')
        FILE_TTL_HOURS = 48
        SESSION_TYPE = 'filesystem'
        SESSION_PERMANENT = True
        MAX_CONTENT_LENGTH = 16 * 1024 * 1024
        ALLOWED_EXTENSIONS = {'yml', 'yaml', 'zip'}

    text = io.StringIO()
    YAML().dump(baseline(), text)
    monkeypatch.setattr(SessionService, 'save_draft', lambda self, session_id, data: False)
    client = create_app(TestConfig).test_client()

    response = client.post('/upload', data={
        'file': (io.BytesIO(text.getvalue().encode()), 'base.yml'),
        'custom_name': 'Imported Policy Name',
        'custom_description': 'Imported policy description long enough for the required form validation.',
    }, content_type='multipart/form-data')

    assert response.status_code == 500
    with client.session_transaction() as sess:
        assert 'session_id' not in sess
