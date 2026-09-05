import uuid

from ruamel.yaml import YAML

from sca.app import create_app


def baseline(checks=None):
    return {
        'policy': {
            'name': 'Báseline',
            'id': 'base',
            'description': 'Déscription',
            'file': 'base.yml',
        },
        'requirements': {
            'title': 'Linux',
            'description': 'Required',
            'condition': 'all',
            'rules': ['f:/etc/passwd'],
        },
        'variables': {'$x': 1},
        'checks': checks if checks is not None else [
            {
                'id': 1,
                'title': 'One | first',
                'condition': 'all',
                'impact': 'Low',
                'rationale': 'A real rationale',
                'rules': ['f:/one'],
                'references': ['ref'],
                'remediation': 'Fix',
                'compliance': [{'cis': ['1.1']}],
                'regex_type': 'pcre2',
            },
            {
                'id': 2,
                'title': 'Two',
                'condition': 'all',
                'impact': 'High',
                'rules': ['f:/two'],
            },
        ],
    }


def write_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as stream:
        YAML().dump(data, stream)


def app_with_session(tmp_path):
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
        ALLOWED_EXTENSIONS = {'yml', 'yaml'}

    app = create_app(TestConfig)
    path = tmp_path / 'uploads' / 'base.yml'
    write_yaml(path, baseline())
    client = app.test_client()
    with client.session_transaction() as sess:
        sess.update(
            session_id=str(uuid.uuid4()),
            baseline_filename='base.yml',
            custom_name='Tailored',
            sanitized_name='a_tailored_policy',
            custom_description='Description',
            decisions={},
        )
    return client
