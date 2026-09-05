from sca.internal.guide import Guide
from sca.internal.sca import Check
from sca.services.sca_service import get_checks, validate_sca_file
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

    assert validate_sca_file(str(path)) == (True, None)
    assert Check.from_dict(data['checks'][0]).compliance == data['checks'][0]['compliance']
    assert get_checks(Guide(str(path)))[0]['compliance'] == data['checks'][0]['compliance']
