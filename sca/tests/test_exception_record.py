import zipfile
from pathlib import Path

from ruamel.yaml import YAML

from sca.tests.helpers import app_with_session, baseline


def test_three_state_review_exports_stable_exception_record(tmp_path):
    data = baseline()
    data['checks'].append({
        'id': 3,
        'title': 'Three',
        'condition': 'all',
        'impact': 'Low',
        'rules': ['f:/three'],
        'compliance': [
            {'cis': ['3.1']},
            {'pci_dss_v4.0': ['1.2.5', '2.2.4', '6.4.1']},
        ],
    })
    data['checks'].append({
        'id': 4,
        'title': 'Four',
        'condition': 'all',
        'impact': 'Low',
        'rules': ['f:/four'],
    })
    client = app_with_session(tmp_path, data)

    for check_id, decision, justification in (
        (3, 'exception', 'Risk accepted for this platform role'),
        (2, 'not_applicable', 'Control does not apply to this platform role'),
        (1, 'exception', 'Risk accepted for this baseline control'),
    ):
        response = client.post('/api/decision', json={
            'check_id': check_id,
            'decision': decision,
            'justification': justification,
        })
        assert response.status_code == 200

    assert response.json['stats']['not_applicable'] == 1
    assert response.json['stats']['reviewed'] == 3
    assert client.post('/api/export').status_code == 400

    assert client.post('/api/decision', json={
        'check_id': 4,
        'decision': 'accepted',
        'justification': '',
    }).status_code == 200
    assert client.post('/api/export').status_code == 200

    with client.session_transaction() as sess:
        first_archive = Path(sess['export_zip_path'])
    with zipfile.ZipFile(first_archive) as bundle:
        record_bytes = bundle.read('a_tailored_policy_exceptions.yml')
        record = YAML(typ='safe').load(record_bytes.decode('utf-8'))
        tailored = YAML(typ='safe').load(
            bundle.read('a_tailored_policy.yml').decode('utf-8'))
        markdown = bundle.read('a_tailored_policy_exceptions.md').decode('utf-8')

    assert 'schema' not in record
    assert [item['check_id'] for item in record['exceptions']] == [1, 3]
    assert [item['check_id'] for item in record['not_applicable']] == [2]
    assert record['exceptions'][0]['compliance'] == data['checks'][0]['compliance']
    assert record['exceptions'][1]['compliance'] == data['checks'][2]['compliance']
    assert 'compliance' not in record['not_applicable'][0]
    assert b'compliance: null' not in record_bytes
    assert [check['id'] for check in tailored['checks']] == [4]
    assert '## Exceptions' in markdown
    assert '## Not Applicable' in markdown
    assert 'pci\\_dss\\_v4.0: 1.2.5, 2.2.4, 6.4.1' in markdown

    assert client.post('/api/export').status_code == 200
    with client.session_transaction() as sess:
        second_archive = Path(sess['export_zip_path'])
    with zipfile.ZipFile(second_archive) as bundle:
        assert bundle.read('a_tailored_policy_exceptions.yml') == record_bytes
