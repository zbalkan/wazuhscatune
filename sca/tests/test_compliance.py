from sca.internal.sca import Check
from sca.services.sca_service import SCAService
from sca.tests.helpers import baseline, write_yaml


def test_compliance_frameworks_are_open_ended_and_preserved(tmp_path):
    data = baseline()
    data['checks'][0]['compliance'] = [
        {'pci_dss': ['2.2.4']},
        {'nist_800_53': ['CM.1']},
        {'future.framework-v1': ['A.1']},
    ]
    path = tmp_path / 'policy.yml'
    write_yaml(path, data)

    assert SCAService.validate_sca_file(str(path)) == (True, None)

    parsed = Check.from_dict(data['checks'][0])
    assert parsed.compliance[0].values == {'pci_dss': ['2.2.4']}
    assert parsed.compliance[1].values == {'nist_800_53': ['CM.1']}
    assert parsed.compliance[2].values == {'future.framework-v1': ['A.1']}


def test_compliance_display_serialization_is_generic():
    parsed = Check.from_dict({
        'id': 1, 'title': 'Check', 'condition': 'all', 'rules': ['f:/one'],
        'compliance': [{'future.framework-v1': ['A.1']}],
    })
    assert SCAService._serialize_compliance(parsed.compliance) == [
        {'future_framework_v1': ['A.1']}
    ]
