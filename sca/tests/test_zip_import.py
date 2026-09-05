import io
import uuid
import zipfile

from ruamel.yaml import YAML

from sca.app import create_app
from sca.tests.helpers import baseline, write_yaml


def _client(tmp_path):
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

    return create_app(TestConfig).test_client()


def _policy_yaml() -> bytes:
    text = io.StringIO()
    YAML().dump(baseline(), text)
    return text.getvalue().encode('utf-8')


def _upload_data(file):
    return {
        'file': file,
        'custom_name': 'Imported Policy Name',
        'custom_description': 'Imported policy description long enough for the required form validation.',
    }


def _upload_zip(tmp_path, archive, name='policy.zip'):
    archive.seek(0)
    return _client(tmp_path).post(
        '/upload',
        data=_upload_data((archive, name)),
        content_type='multipart/form-data',
    )


def test_exported_zip_policy_can_be_imported(tmp_path):
    client = _client(tmp_path)
    write_yaml(tmp_path / 'uploads' / 'base.yml', baseline())
    with client.session_transaction() as sess:
        sess.update(
            session_id=str(uuid.uuid4()),
            baseline_filename='base.yml',
            custom_name='Imported Policy Exceptions',
            sanitized_name='imported_policy_exceptions',
            custom_description='Imported policy description long enough for the required form validation.',
            decisions={},
        )

    for check_id in (1, 2):
        response = client.post('/api/decision', json={
            'check_id': check_id,
            'decision': 'accepted',
            'justification': '',
        })
        assert response.status_code == 200

    export_response = client.post('/api/export')
    assert export_response.status_code == 200
    with client.session_transaction() as sess:
        archive_path = sess['export_zip_path']

    with open(archive_path, 'rb') as stream:
        archive = io.BytesIO(stream.read())

    response = client.post(
        '/upload',
        data=_upload_data((archive, 'imported_policy_exceptions_export.zip')),
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    assert response.json['success'] is True


def test_zip_import_requires_exactly_one_policy_yaml(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('one.yml', _policy_yaml())
        bundle.writestr('two.yml', _policy_yaml())

    response = _upload_zip(tmp_path, archive, 'ambiguous.zip')
    assert response.status_code == 400
    assert 'exactly one policy YAML' in response.json['error']


def test_zip_import_rejects_too_many_members(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('policy.yml', _policy_yaml())
        for index in range(128):
            bundle.writestr(f'empty-{index}.txt', '')

    response = _upload_zip(tmp_path, archive, 'many-members.zip')
    assert response.status_code == 400
    assert 'too many files' in response.json['error']


def test_zip_import_rejects_large_decompressed_policy(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr('policy.yml', b'a' * (16 * 1024 * 1024 + 1))

    response = _upload_zip(tmp_path, archive, 'compressed-large.zip')
    assert response.status_code == 400
    assert 'maximum upload size' in response.json['error']


def test_zip_member_path_is_not_extracted(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('../../outside.yml', _policy_yaml())

    response = _upload_zip(tmp_path, archive, 'traversal.zip')
    assert response.status_code == 200
    assert not (tmp_path / 'outside.yml').exists()
    assert len(list((tmp_path / 'uploads').glob('*_outside.yml'))) == 1


def test_unsupported_zip_member_returns_bad_request(tmp_path, monkeypatch):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('policy.yml', _policy_yaml())
    archive.seek(0)

    def unsupported(*args, **kwargs):
        raise NotImplementedError('unsupported compression')

    monkeypatch.setattr(zipfile.ZipFile, 'open', unsupported)
    response = _client(tmp_path).post(
        '/upload',
        data=_upload_data((archive, 'unsupported.zip')),
        content_type='multipart/form-data',
    )

    assert response.status_code == 400
    assert 'unsupported ZIP archive' in response.json['error']
