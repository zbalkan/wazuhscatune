import uuid

from sca.services.session_service import SessionService
from sca.tests.helpers import app_with_session


def _persist_active_draft(client, tmp_path):
    with client.session_transaction() as sess:
        session_id = sess['session_id']
        data = SessionService.serialize_session_data(
            sess['baseline_filename'], sess['custom_name'], sess['sanitized_name'],
            sess['custom_description'], sess['decisions'])
    service = SessionService(str(tmp_path / 'drafts'))
    assert service.save_draft(session_id, data)
    return session_id, service


def test_delete_previous_draft_removes_draft_and_baseline(tmp_path):
    client = app_with_session(tmp_path)
    with client.session_transaction() as sess:
        active_id = sess['session_id']
    previous_id = str(uuid.uuid4())
    previous_baseline = tmp_path / 'uploads' / 'previous.yml'
    previous_baseline.write_text('policy: {}', encoding='utf-8')
    service = SessionService(str(tmp_path / 'drafts'))
    assert service.save_draft(previous_id, {
        'baseline_filename': 'previous.yml', 'custom_name': 'Previous policy',
        'sanitized_name': 'previous_policy', 'custom_description': 'Description',
        'decisions': {}})

    response = client.delete(f'/api/drafts/{previous_id}')

    assert response.status_code == 200
    assert service.load_draft(previous_id) is None
    assert not previous_baseline.exists()
    with client.session_transaction() as sess:
        assert sess['session_id'] == active_id


def test_delete_active_draft_clears_session(tmp_path):
    client = app_with_session(tmp_path)
    session_id, service = _persist_active_draft(client, tmp_path)

    response = client.delete(f'/api/drafts/{session_id}')

    assert response.status_code == 200
    assert service.load_draft(session_id) is None
    assert not (tmp_path / 'uploads' / 'base.yml').exists()
    with client.session_transaction() as sess:
        assert dict(sess) == {}


def test_delete_draft_rejects_invalid_and_missing_ids(tmp_path):
    client = app_with_session(tmp_path)
    assert client.delete('/api/drafts/not-a-uuid').status_code == 400
    assert client.delete(f'/api/drafts/{uuid.uuid4()}').status_code == 404
