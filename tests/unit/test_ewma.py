import pytest

from datetime import UTC, datetime

from blockpulse.chain_health.application.ewma import (
    change_point_score,
    detect_change_point_anomalies,
    ewma,
)
from blockpulse.domain import FeatureSnapshot


def test_ewma_is_deterministic() -> None:
    assert ewma([0, 10, 10], alpha=0.5) == [0, 5, 7.5]


def test_change_point_score_detects_regime_shift() -> None:
    assert change_point_score([1, 1, 1], 5) == float("inf")


def test_ewma_validates_alpha() -> None:
    with pytest.raises(ValueError, match="alpha"):
        ewma([1, 2], alpha=0)


def test_change_point_detector_returns_traceable_score() -> None:
    def feature(value: float, feature_id: str) -> FeatureSnapshot:
        return FeatureSnapshot(
            feature_id=feature_id,
            feature_name="rpc_error_rate",
            feature_version="rpc-v1",
            entity_type="chain",
            entity_id="8453",
            chain_id=8453,
            measured_at=datetime(2026, 10, 21, 9, 0, tzinfo=UTC),
            window_minutes=15,
            value=value,
            source_observation_ids=[feature_id],
        )

    anomalies = detect_change_point_anomalies(
        [feature(5, "current")], [feature(1, "h1"), feature(1, "h2"), feature(1, "h3")]
    )

    assert len(anomalies) == 1
    assert anomalies[0].detector_version == "ewma-v1"
