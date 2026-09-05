"""Regression tests for remediation work."""
import copy
import zipfile
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from sca.internal.guide import Guide
from sca.internal.loosening import Check
from sca.internal.review import ReviewDecision, escape_markdown_cell, normalize_decisions
from sca.services.export_service import ExportService
from sca.services.sca_service import SCAService
from sca.tests.helpers import app_with_session, baseline, write_yaml


def test_invalid_decisions_are_rejected(tmp_path):
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
    with pytest.raises((TypeError, ValueError)):
        ReviewDecision.create(1, decision, justification)
