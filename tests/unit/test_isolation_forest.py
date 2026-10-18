import pytest

from blockpulse.chain_health.application.isolation_forest import IsolationForestDetector
from blockpulse.domain import FeatureVector


def vector(vector_id: str, first: float, second: float) -> FeatureVector:
    from datetime import UTC, datetime

    return FeatureVector(
        vector_id=vector_id,
        entity_type="chain",
        entity_id="8453",
        chain_id=8453,
        measured_at=datetime(2026, 10, 18, 9, 0, tzinfo=UTC),
        feature_values={"error_rate": first, "latency": second},
        feature_ids={"error_rate": f"{vector_id}-error", "latency": f"{vector_id}-latency"},
    )


def test_isolation_forest_is_seeded_and_traceable() -> None:
    detector = IsolationForestDetector(["error_rate", "latency"], n_estimators=50)
    training = [vector(f"train-{index}", 0.1 + index * 0.001, 100 + index) for index in range(20)]
    detector.fit(training)

    anomalies = detector.detect(training + [vector("outlier", 0.99, 5000)])

    assert anomalies
    assert all(item.detector_version == "iforest-v1" for item in anomalies)


def test_isolation_forest_requires_fit() -> None:
    with pytest.raises(RuntimeError, match="fitted"):
        IsolationForestDetector(["error_rate"]).detect([])
