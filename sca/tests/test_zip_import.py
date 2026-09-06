import hashlib
import io
import uuid
import zipfile

from ruamel.yaml import YAML

from sca.app import create_app
from sca.routes.upload import sanitize_policy_name
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


def _yaml_bytes(value) -> bytes:
    text = io.StringIO()
    YAML().dump(value, text)
    return text.getvalue().encode('utf-8')


def _policy_yaml() -> bytes:
    return _yaml_bytes(baseline())


def _exception_record(filename: str, digest: str | None = None) -> bytes:
    tailored_policy = {
        'name': 'Imported Policy',
        'id': 'policy',
        'file': filename,
    }
    if digest is not None:
        tailored_policy['sha256'] = digest
    return _yaml_bytes({'tailored_policy': tailored_policy})


def _upload_data(file):
    return {
        'file': file,
        'custom_name': 'Imported Policy Name',
        'custom_description': 'Imported policy description long enough for the required form validation.',
    }


def _upload_zip(tmp_path, archive, filename='archive.zip'):
    archive.seek(0)
    return _client(tmp_path).post(
        '/upload',
        data=_upload_data((archive, filename)),
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


def test_zip_import_rejects_tampered_exported_policy(tmp_path):
    original = _policy_yaml()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('policy.yml', original + b'\n# modified after export\n')
        bundle.writestr(
            'policy_exceptions.yml',
            _exception_record('policy.yml', hashlib.sha256(original).hexdigest()),
        )

    response = _upload_zip(tmp_path, archive, 'tampered.zip')
    assert response.status_code == 400
    assert 'SHA-256 does not match' in response.json['error']


def test_zip_import_accepts_legacy_exception_record_without_digest(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('policy.yml', _policy_yaml())
        bundle.writestr('policy_exceptions.yml', _exception_record('policy.yml'))

    response = _upload_zip(tmp_path, archive, 'legacy.zip')
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
            bundle.writestr(f'extra-{index}.txt', '')

    response = _upload_zip(tmp_path, archive, 'many.zip')
    assert response.status_code == 400
    assert 'too many files' in response.json['error']


def test_zip_import_rejects_oversized_expansion(tmp_path):
    archive = io.BytesIO()
    payload = _policy_yaml() + b'\n#' + b'x' * (16 * 1024 * 1024)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr('policy.yml', payload)

    response = _upload_zip(tmp_path, archive, 'bomb.zip')
    assert response.status_code == 400
    assert 'maximum upload size' in response.json['error']


def test_zip_traversal_member_is_stored_safely(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('../../outside.yml', _policy_yaml())

    response = _upload_zip(tmp_path, archive, 'traversal.zip')
    assert response.status_code == 200
    assert not (tmp_path / 'outside.yml').exists()
    assert len(list((tmp_path / 'uploads').glob('*_outside.yml'))) == 1


def test_control_characters_are_removed_from_policy_filename():
    sanitized = sanitize_policy_name('Valid Policy\x00\n<script>')
    assert sanitized == 'valid_policy_script'
    assert '\x00' not in sanitized and '\n' not in sanitized


def test_unsupported_zip_member_returns_bad_request(tmp_path, monkeypatch):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('policy.yml', _policy_yaml())

    def unsupported(*args, **kwargs):
        raise NotImplementedError('unsupported compression')

    monkeypatch.setattr(zipfile.ZipFile, 'open', unsupported)
    response = _upload_zip(tmp_path, archive, 'unsupported.zip')
    assert response.status_code == 400
    assert 'unsupported ZIP archive' in response.json['error']
