from sca.tests.helpers import app_with_session


def test_review_uses_reading_pane_and_save_next(tmp_path):
    response = app_with_session(tmp_path).get('/review')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="check-list"' in html
    assert 'class="reading-pane"' in html
    assert 'id="save-next-btn"' in html
    assert 'Save &amp; Next' in html
    assert 'id="check-modal"' not in html


def test_review_decisions_button_is_disabled_until_complete(tmp_path):
    client = app_with_session(tmp_path)
    assert 'id="review-decisions-btn" disabled' in client.get('/review').get_data(as_text=True)

    with client.session_transaction() as sess:
        sess['decisions'] = {
            '1': {'decision': 'accepted'},
            '2': {'decision': 'accepted'},
        }

    assert 'id="review-decisions-btn" disabled' not in client.get('/review').get_data(as_text=True)
