import copy
import os
import time
import zipfile
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from sca.internal.guide import Guide, escape_markdown_cell
from sca.internal.review import ReviewDecision, normalize_decisions
from sca.internal.sca import Check
from sca.services.export_service import ExportService
from sca.services.sca_service import SCAService
from sca.services.session_service import SessionService, contained_path, validate_contained
from sca.tests.helpers import app_with_session, baseline, write_yaml


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
    assert SCAService.validate_sca_file(str(path)) == (
        False,
        'Duplicate check ID: 1',
    )
    data = baseline()
    data['checks'][0]['id'] = '1'
    write_yaml(path, data)
    valid, message = SCAService.validate_sca_file(str(path))
    assert not valid and 'integer' in message


def test_validation_accepts_dotted_compliance_keys(tmp_path):
    data = baseline()
    data['checks'][0]['compliance'] = [
        {'cmmc_v2.0': ['AC.L1-3.1.1']},
        {'pci_dss_v3.2.1': ['7.1']},
        {'pci_dss_v4.0': ['7.1']},
    ]
    path = tmp_path / 'base.yml'
    write_yaml(path, data)
    valid, message = SCAService.validate_sca_file(str(path))
    assert (valid, message) == (True, None)

    guide = Guide(str(path))
    checks = SCAService.get_checks(guide)
    compliance = checks[0]['compliance']
    assert compliance[0] == {'cmmc_v2_0': ['AC.L1-3.1.1']}
    assert compliance[1] == {'pci_dss_v3_2_1': ['7.1']}
    assert compliance[2] == {'pci_dss_v4_0': ['7.1']}


def test_decision_api_validation_and_normalized_stats(tmp_path):
    client = app_with_session(tmp_path)
    invalid = [
        None,
        {},
        {'check_id': 1, 'decision': 'invalid'},
        {'check_id': 1, 'decision': 'exception', 'justification': 'short'},
    ]
    for body in invalid:
        response = client.post('/api/decision', json=body)
        assert 400 <= response.status_code < 500
        with client.session_transaction() as sess:
            assert sess['decisions'] == {}
    assert client.post(
        '/api/decision',
        data='{',
        content_type='application/json',
    ).status_code == 400
    assert client.post(
        '/api/decision',
        json={'check_id': -1, 'decision': 'accepted'},
    ).status_code == 404
    response = client.post(
        '/api/decision',
        json={'check_id': '1', 'decision': 'accepted'},
    )
    assert response.status_code == 200
    assert response.json['check_id'] == '1'
    with client.session_transaction() as sess:
        assert sess['decisions']['1'] == {'decision': 'accepted'}
    response = client.post(
        '/api/decision',
        json={
            'check_id': 1,
            'decision': 'exception',
            'justification': 'Needed | for\nlegacy \\ app',
        },
    )
    assert response.status_code == 200
    assert response.json['stats'] == {
        'total': 2,
        'accepted': 0,
        'exceptions': 1,
        'unreviewed': 1,
        'effective_included': 1,
        'reviewed': 1,
        'review_completion': 50.0,
    }
    response = client.post(
        '/api/decision',
        json={'check_id': 1, 'decision': 'accepted'},
    )
    assert response.json['decision'] == {'decision': 'accepted'}
    assert response.json['stats']['accepted'] == 1


def test_decision_api_rejects_all_invalid_justification_types(tmp_path):
    client = app_with_session(tmp_path)
    for value in (None, 1, [], {}, 'x' * 1001):
        response = client.post(
            '/api/decision',
            json={
                'check_id': 1,
                'decision': 'exception',
                'justification': value,
            },
        )
        assert response.status_code == 400


def test_export_invariants_provenance_markdown_and_archive(tmp_path):
    source = baseline()
    original = copy.deepcopy(source)
    path = tmp_path / 'base.yml'
    export_root = str(tmp_path / 'exports')
    write_yaml(path, source)
    guide = Guide(str(path))
    loosening = SCAService.create_loosening(
        'Tâiloréd policy',
        'tailored',
        'Unicode – açıklama',
    )
    check = Check.from_dict(source['checks'][0])
    SCAService.add_decision(
        loosening,
        check,
        'Needed | because\nlegacy \\ app',
    )
    paths = ExportService.generate_files(guide, loosening, 'tailored', export_root)
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
    markdown = Path(exceptions_md).read_text(encoding='utf-8')
    assert r'Needed \| because<br>legacy \\ app' in markdown
    archive = ExportService.create_zip_archive(paths[:3], 'result.zip', export_root)
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == {
            'tailored.yml',
            'tailored_exceptions.yml',
            'tailored_exceptions.md',
        }
    assert source == original


def test_markdown_escape():
    assert escape_markdown_cell('a|b\r\nc\\d') == r'a\|b<br>c\\d'


@pytest.mark.parametrize(
    'decision,justification,expected',
    [
        ('accepted', 'discarded text', {'decision': 'accepted'}),
        (
            'exception',
            'A valid reason',
            {'decision': 'exception', 'justification': 'A valid reason'},
        ),
    ],
)
def test_typed_decision_normalization(decision, justification, expected):
    value = ReviewDecision.create(1, decision, justification)
    assert value.to_session() == expected
    assert normalize_decisions({'1': expected, '999': expected}, {1}) == {
        1: value,
    }


@pytest.mark.parametrize(
    'decision,justification',
    [
        ('other', ''),
        ('exception', ''),
        ('exception', 'short'),
        ('exception', 12),
        ('accepted', 'x' * 1001),
        ('exception', '!' * 20),
        ('exception', 'aaaaaaaaaaaa'),
        ('exception', '..........'),
    ],
)
def test_typed_decision_rejects_invalid_values(decision, justification):
    with pytest.raises(ValueError):
        ReviewDecision.create(1, decision, justification)


def test_decision_api_rejects_meaningless_exception_justification(tmp_path):
    client = app_with_session(tmp_path)
    response = client.post(
        '/api/decision',
        json={
            'check_id': 1,
            'decision': 'exception',
            'justification': '!' * 20,
        },
    )
    assert response.status_code == 400
    with client.session_transaction() as sess:
        assert sess['decisions'] == {}


def test_validation_rejects_nested_optional_types(tmp_path):
    path = tmp_path / 'base.yml'
    cases = [
        ('description', []),
        ('rationale', {}),
        ('rules', []),
        ('compliance', ['not-a-mapping']),
        ('compliance', [{'cis': '1.1'}]),
    ]
    for field, value in cases:
        data = baseline()
        data['checks'][0][field] = value
        write_yaml(path, data)
        assert SCAService.validate_sca_file(str(path))[0] is False


def test_multiple_and_second_export_preserve_source(tmp_path):
    source = baseline([
        {
            'id': number,
            'title': f'Check {number}',
            'condition': 'all',
            'impact': 'Low',
            'rules': [f'f:/{number}'],
        }
        for number in range(1, 5)
    ])
    path = tmp_path / 'base.yml'
    write_yaml(path, source)
    guide = Guide(str(path))
    tailoring = SCAService.create_loosening(
        'Tailored Policy',
        'tailored',
        'Description',
    )
    for check_id in (1, 4):
        SCAService.add_decision(
            tailoring,
            Check.from_dict(source['checks'][check_id - 1]),
            f'Valid reason for {check_id}',
        )
    first = ExportService.generate_files(
        guide,
        tailoring,
        'first',
        str(tmp_path / 'exports'),
    )[0]
    empty = SCAService.create_loosening(
        'Second Policy',
        'second',
        'Description',
    )
    second = ExportService.generate_files(
        guide,
        empty,
        'second',
        str(tmp_path / 'exports'),
    )[0]
    yaml = YAML(typ='safe')
    assert [
        c['id']
        for c in yaml.load(Path(first).read_text(encoding='utf-8'))['checks']
    ] == [2, 3]
    assert [
        c['id']
        for c in yaml.load(Path(second).read_text(encoding='utf-8'))['checks']
    ] == [1, 2, 3, 4]


def test_containment_and_expiry(tmp_path):
    root = tmp_path / 'owned'
    root.mkdir()
    assert contained_path(str(root), 'safe.yml').parent == root
    with pytest.raises(ValueError):
        contained_path(str(root), '../outside')
    with pytest.raises(ValueError):
        validate_contained(str(root), str(tmp_path / 'outside'))
    expired = root / 'expired'
    active = root / 'active'
    expired.write_text('old', encoding='utf-8')
    active.write_text('new', encoding='utf-8')
    os.utime(expired, (time.time() - 7200, time.time() - 7200))
    SessionService.cleanup_expired([str(root)], 1)
    assert not expired.exists() and active.exists()


def test_archive_fails_for_missing_artifact(tmp_path):
    with pytest.raises(FileNotFoundError):
        ExportService.create_zip_archive(
            [str(tmp_path / 'missing')],
            'result.zip',
            str(tmp_path),
        )


def test_export_route_rejects_corrupt_state_and_all_exceptions(tmp_path):
    client = app_with_session(tmp_path)
    with client.session_transaction() as sess:
        sess['decisions'] = {
            '1': {
                'decision': 'exception',
                'justification': 'too short',
            },
        }
    assert client.post('/api/export').status_code == 400
    with client.session_transaction() as sess:
        sess['decisions'] = {
            '1': {
                'decision': 'exception',
                'justification': 'A valid first reason',
            },
            '2': {
                'decision': 'exception',
                'justification': 'A valid second reason',
            },
        }
    response = client.post('/api/export')
    assert response.status_code == 400
    assert 'remain included' in response.json['error']


def test_draft_round_trip_and_recovery(tmp_path):
    client = app_with_session(tmp_path)
    with client.session_transaction() as sess:
        session_id = sess['session_id']
    assert client.post('/api/save-draft').status_code == 200
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get(f'/recover/{session_id}')
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess['baseline_filename'] == 'base.yml'
        assert sess['sanitized_name'] == 'a_tailored_policy'


def test_parser_supported_fields_and_missing_optionals():
    parsed = Check.from_dict(baseline()['checks'][0])
    assert parsed.description is None
    assert parsed.rationale == 'A real rationale'
    assert parsed.remediation == 'Fix'
    assert parsed.references == ['ref']
    assert parsed.rules == ['f:/one']
    assert parsed.regex_type == 'pcre2'
    assert parsed.compliance[0].cis == ['1.1']
