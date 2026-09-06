import uuid
from pathlib import Path

from sca.services.session_service import SessionService


def test_save_draft_replaces_existing_file_without_temp_residue(tmp_path):
    service = SessionService(str(tmp_path))
    session_id = str(uuid.uuid4())
    first = {'custom_name': 'First'}
    second = {'custom_name': 'Second'}

    assert service.save_draft(session_id, first)
    assert service.save_draft(session_id, second)

    loaded = service.load_draft(session_id)
    assert loaded['custom_name'] == 'Second'
    assert list(Path(tmp_path).glob('*.tmp')) == []
    assert len(list(Path(tmp_path).glob('*.json'))) == 1
