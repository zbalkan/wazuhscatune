import io
import zipfile

from ruamel.yaml import YAML

from sca.app import create_app
from sca.tests.helpers import baseline


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


def test_exported_zip_policy_can_be_imported(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('tailored.yml', _policy_yaml())
        bundle.writestr('tailored_exceptions.yml', 'exceptions: []\n')
    archive.seek(0)

    response = _client(tmp_path).post(
        '/upload',
        data=_upload_data((archive, 'tailored_export.zip')),
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    assert response.json['success'] is True


def test_zip_import_requires_exactly_one_policy_yaml(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('one.yml', _policy_yaml())
        bundle.writestr('two.yml', _policy_yaml())
    archive.seek(0)

    response = _client(tmp_path).post(
        '/upload',
        data=_upload_data((archive, 'ambiguous.zip')),
        content_type='multipart/form-data',
    )

    assert response.status_code == 400
    assert 'exactly one policy YAML' in response.json['error']
