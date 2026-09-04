import copy
import io
import os
import zipfile

from ruamel.yaml import YAML

from app import create_app
from internal.guide import Guide, escape_markdown_cell
from internal.sca import Check
from services.export_service import ExportService
from services.sca_service import SCAService


def baseline(checks=None):
    return {
        'policy': {'name': 'Báseline', 'id': 'base', 'description': 'Déscription', 'file': 'base.yml'},
        'requirements': {'title': 'Linux', 'description': 'Required', 'condition': 'all'},
        'variables': {'$x': 1},
        'checks': checks or [
            {'id': 1, 'title': 'One | first', 'condition': 'all', 'impact': 'Low',
             'rationale': 'A real rationale', 'rules': ['f:/one'],
             'references': ['ref'], 'remediation': 'Fix',
             'compliance': [{'cis': ['1.1']}], 'regex_type': 'pcre2'},
            {'id': 2, 'title': 'Two', 'condition': 'all', 'impact': 'High', 'rules': ['f:/two']},
        ],
    }


def write_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as stream:
        YAML().dump(data, stream)


def test_rationale_populated_empty_and_absent(tmp_path):
    data = baseline()
    data['checks'][1]['rationale'] = ''
    path = tmp_path / 'base.yml'
    write_yaml(path, data)
    guide = Guide(str(path))
    parsed = [Check.from_dict(item) for item in guide.__sca_yml__['checks']]
    assert parsed[0].rationale == 'A real rationale'
    assert parsed[1].rationale is None
    del data['checks'][1]['rationale']
    assert Check.from_dict(data['checks'][1]).rationale is None
    assert SCAService.get_checks(guide)[1]['rationale'] == ''


def test_validation_rejects_incomplete_and_duplicate_checks(tmp_path):
    path = tmp_path / 'base.yml'
    data = baseline()
    data['checks'][1]['id'] = 1
    write_yaml(path, data)
    assert SCAService.validate_sca_file(str(path)) == (False, 'Duplicate check ID: 1')
    del data['requirements']
    write_yaml(path, data)
    valid, message = SCAService.validate_sca_file(str(path))
    assert not valid and 'requirements' in message
    data = baseline()
    data['checks'][0]['id'] = '1'
    write_yaml(path, data)
    valid, message = SCAService.validate_sca_file(str(path))
    assert not valid and 'integer' in message


def app_with_session(tmp_path):
    class TestConfig:
        TESTING = True
        SECRET_KEY = 'test'
        UPLOAD_FOLDER = str(tmp_path / 'uploads')
        DRAFT_FOLDER = str(tmp_path / 'drafts')
        SESSION_FILE_DIR = str(tmp_path / 'sessions')
        ALLOWED_EXTENSIONS = {'yml', 'yaml'}
    app = create_app(TestConfig)
    path = tmp_path / 'base.yml'
    write_yaml(path, baseline())
    client = app.test_client()
    with client.session_transaction() as sess:
        sess.update(session_id='abc', baseline_path=str(path), custom_name='A tailored policy',
                    custom_description='A detailed tailored policy description', decisions={})
    return client


def test_decision_api_validation_and_normalized_stats(tmp_path):
    client = app_with_session(tmp_path)
    invalid = [None, {}, {'check_id': '1', 'decision': 'accepted'},
               {'check_id': 1, 'decision': 'invalid'},
               {'check_id': 1, 'decision': 'exception', 'justification': 'short'}]
    for body in invalid:
        response = client.post('/api/decision', json=body)
        assert 400 <= response.status_code < 500
    assert client.post('/api/decision', json={'check_id': -1, 'decision': 'accepted'}).status_code == 404
    response = client.post('/api/decision', json={'check_id': 1, 'decision': 'exception',
                                                   'justification': 'Needed | for\nlegacy \\ app'})
    assert response.status_code == 200
    assert response.json['stats'] == {'total': 2, 'accepted': 0, 'exceptions': 1,
        'unreviewed': 1, 'effective_included': 1, 'reviewed': 1, 'review_completion': 50.0}
    response = client.post('/api/decision', json={'check_id': 1, 'decision': 'accepted'})
    assert response.json['decision'] == {'decision': 'accepted'}


def test_export_invariants_provenance_markdown_and_archive(tmp_path):
    source = baseline()
    original = copy.deepcopy(source)
    path = tmp_path / 'base.yml'
    write_yaml(path, source)
    guide = Guide(str(path))
    loosening = SCAService.create_loosening('Tâiloréd policy', 'tailored', 'Unicode – açıklama')
    check = Check.from_dict(source['checks'][0])
    SCAService.add_decision(loosening, check, 'Needed | because\nlegacy \\ app')
    paths = ExportService.generate_files(guide, loosening, 'tailored')
    custom, exceptions_yml, exceptions_md, _ = paths
    yaml = YAML(typ='safe')
    with open(custom, encoding='utf-8') as stream:
        tailored = yaml.load(stream)
    assert [c['id'] for c in tailored['checks']] == [2]
    assert tailored['checks'][0] == original['checks'][1]
    with open(path, encoding='utf-8') as stream:
        assert yaml.load(stream) == original
    with open(exceptions_yml, encoding='utf-8') as stream:
        record = yaml.load(stream)
    assert record['exceptions'][0]['check_id'] == 1
    assert len(record['baseline']['sha256']) == 64
    assert record['tailored_policy']['id'] == 'tailored'
    markdown = open(exceptions_md, encoding='utf-8').read()
    assert r'Needed \| because<br>legacy \\ app' in markdown
    archive = ExportService.create_zip_archive(paths[:3], 'result.zip')
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == {'tailored.yml', 'tailored_exceptions.yml', 'tailored_exceptions.md'}
    assert source == original


def test_markdown_escape():
    assert escape_markdown_cell('a|b\r\nc\\d') == r'a\|b<br>c\\d'
