import pytest

from sca.internal.review import DecisionType, ReviewDecision, normalize_decisions
from sca.services.session_service import SessionService
from sca.tests.helpers import app_with_session


@pytest.mark.parametrize(('raw', 'message'), [
    (None, 'Review state must be a mapping'),
    ({'bad': {'decision': 'accepted'}}, 'Invalid decision check ID'),
    ({'999': {'decision': 'accepted'}}, 'Unknown decision check ID'),
    ({1: {'decision': 'accepted'}, '1': {'decision': 'accepted'}}, 'Duplicate review state'),
    ({'1': 'accepted'}, 'Invalid review state'),
    ({'1': {'decision': 'unknown'}}, 'Field decision'),
])
def test_review_state_rejects_malformed_input(raw, message):
    with pytest.raises(ValueError, match=message):
        normalize_decisions(raw, {1, 2})


def test_partial_review_state_is_valid():
    normalized = normalize_decisions({'1': {'decision': 'accepted'}}, {1, 2})

    assert set(normalized) == {1}
    assert normalized[1].decision is DecisionType.ACCEPTED


@pytest.mark.parametrize('justification', ['short', 'aaaaaaaaaaaa', 'x' * 1001])
def test_not_applicable_reuses_removing_justification_validation(justification):
    with pytest.raises(ValueError):
        ReviewDecision.create(1, 'not_applicable', justification)


def test_review_page_discards_invalid_stored_state(tmp_path):
    client = app_with_session(tmp_path)
    with client.session_transaction() as sess:
        session_id = sess['session_id']
        sess['decisions'] = {
            '1': {'decision': 'exception', 'justification': 'short'},
        }
        sess['record_generated_at'] = 'stale'

    response = client.get('/review')

    assert response.status_code == 200
    assert b'Stored review state was invalid and has been discarded' in response.data
    with client.session_transaction() as sess:
        assert sess['decisions'] == {}
        assert 'record_generated_at' not in sess
    draft = SessionService(str(tmp_path / 'drafts')).load_draft(session_id)
    assert draft is not None
    assert draft['decisions'] == {}
