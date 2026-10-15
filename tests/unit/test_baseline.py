from datetime import UTC, datetime, timedelta

from blockpulse.chain_health.application.baseline import detect_robust_anomalies, robust_z_score
from blockpulse.domain import FeatureSnapshot, HealthStatus


def make_feature(value: float, minutes: int, feature_id: str) -> FeatureSnapshot:
    return FeatureSnapshot(
        feature_id=feature_id,
        feature_name="rpc_error_rate",
        feature_version="rpc-v1",
        entity_type="chain",
        entity_id="8453",
        chain_id=8453,
        measured_at=datetime(2026, 10, 15, 9, 0, tzinfo=UTC) + timedelta(minutes=minutes),
        window_minutes=15,
        value=value,
        source_observation_ids=[feature_id],
    )


def test_robust_z_score_uses_median_absolute_deviation() -> None:
    assert robust_z_score(1.0, [0.1, 0.1, 0.1, 0.1]) == float("inf")


def test_baseline_returns_traceable_anomaly() -> None:
    history = [make_feature(0.1, index, f"h-{index}") for index in range(4)]
    current = [make_feature(0.8, 10, "current")]

    anomalies = detect_robust_anomalies(current, history)

    assert len(anomalies) == 1
    assert anomalies[0].severity is HealthStatus.CRITICAL
    assert anomalies[0].feature_ids == ["current"]
