import pytest

from blockpulse.chain_health.application.ewma import change_point_score, ewma


def test_ewma_is_deterministic() -> None:
    assert ewma([0, 10, 10], alpha=0.5) == [0, 5, 7.5]


def test_change_point_score_detects_regime_shift() -> None:
    assert change_point_score([1, 1, 1], 5) == float("inf")


def test_ewma_validates_alpha() -> None:
    with pytest.raises(ValueError, match="alpha"):
        ewma([1, 2], alpha=0)
