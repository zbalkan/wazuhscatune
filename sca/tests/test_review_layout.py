from pathlib import Path

from sca.tests.helpers import app_with_session


def test_review_uses_reading_pane_and_save_next(tmp_path):
    response = app_with_session(tmp_path).get('/review')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<body class="review-layout">' in html
    assert 'id="check-list"' in html
    assert 'class="reading-pane"' in html
    assert 'id="save-next-btn"' in html
    assert 'Save &amp; Next' in html
    assert html.index('class="reading-pane-actions"') < html.index('class="reading-pane-content"')
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


def test_review_layout_has_short_viewport_fallback():
    css = (Path(__file__).parents[1] / 'static' / 'css' / 'components.css').read_text()

    assert 'grid-template-rows: minmax(180px, 38%) minmax(0, 1fr);' in css
    assert '@media (max-height: 640px)' in css
    assert 'overflow-y: auto;' in css
    assert 'height: clamp(300px, 65vh, 420px);' in css
