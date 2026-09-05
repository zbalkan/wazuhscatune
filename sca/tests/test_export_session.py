import pytest

from sca.tests.helpers import app_with_session


@pytest.mark.parametrize('field,value', [
    ('custom_name', None),
    ('custom_name', 7),
    ('custom_description', None),
    ('custom_description', []),
])
def test_export_rejects_corrupt_required_session_fields(tmp_path, field, value):
    client = app_with_session(tmp_path)
    with client.session_transaction() as sess:
        sess[field] = value

    response = client.post('/api/export')

    assert response.status_code == 400
    assert 'invalid' in response.json['error'].lower()


@pytest.mark.parametrize('stored', [None, '', 'INVALID NAME!'])
def test_export_regenerates_missing_or_invalid_sanitized_name(tmp_path, stored):
    client = app_with_session(tmp_path)
    with client.session_transaction() as sess:
        sess['custom_name'] = 'Tailored Policy Name'
        if stored is None:
            sess.pop('sanitized_name', None)
        else:
            sess['sanitized_name'] = stored

    response = client.post('/api/export')

    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess['export_zip_filename'] == 'tailored_policy_name_export.zip'


def test_export_does_not_stringify_missing_sanitized_name(tmp_path):
    client = app_with_session(tmp_path)
    with client.session_transaction() as sess:
        sess.pop('sanitized_name', None)

    response = client.post('/api/export')

    assert response.status_code == 200
    assert response.json['success'] is True
