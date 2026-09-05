from sca.tests.helpers import app_with_session


def test_incomplete_review_cannot_open_approval_or_export(tmp_path):
    client = app_with_session(tmp_path)

    approval = client.get('/approval')
    export = client.post('/api/export')

    assert approval.status_code == 302
    assert approval.headers['Location'].endswith('/review')
    assert export.status_code == 400
    assert export.json['error'] == 'All checks must be reviewed before export.'


def test_complete_review_can_open_approval(tmp_path):
    client = app_with_session(tmp_path)
    with client.session_transaction() as sess:
        sess['decisions'] = {
            '1': {'decision': 'accepted'},
            '2': {'decision': 'accepted'},
        }

    response = client.get('/approval')

    assert response.status_code == 200
