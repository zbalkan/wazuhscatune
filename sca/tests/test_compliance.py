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
    assert parsed.compliance == data['checks'][0]['compliance']
    assert SCAService._serialize_compliance(parsed.compliance) == data['checks'][0]['compliance']
