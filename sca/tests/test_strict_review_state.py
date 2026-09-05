import pytest

from sca.internal.review import normalize_decisions


def test_strict_review_state_rejects_unknown_check_id():
    with pytest.raises(ValueError, match='Unknown decision check ID'):
        normalize_decisions(
            {'999': {'decision': 'accepted'}},
            {1, 2},
            strict=True,
        )
