from datetime import UTC, datetime

from blockpulse.chain_health.application.vectorization import build_feature_vectors
from blockpulse.domain import FeatureSnapshot


def feature(name: str, value: float, feature_id: str) -> FeatureSnapshot:
    return FeatureSnapshot(
        feature_id=feature_id,
        feature_name=name,
        feature_version="rpc-v1",
        entity_type="chain",
        entity_id="8453",
        chain_id=8453,
        measured_at=datetime(2026, 10, 19, 9, 0, tzinfo=UTC),
        window_minutes=15,
        value=value,
        source_observation_ids=[f"observation-{feature_id}"],
    )


def test_vectorization_aligns_features_and_keeps_ids() -> None:
    vectors = build_feature_vectors(
        [feature("error_rate", 0.1, "f1"), feature("latency", 100, "f2")],
        ["error_rate", "latency"],
    )

    assert len(vectors) == 1
    assert vectors[0].feature_values == {"error_rate": 0.1, "latency": 100}
    assert vectors[0].feature_ids["latency"] == "f2"


def test_vectorization_skips_incomplete_windows() -> None:
    assert build_feature_vectors([feature("error_rate", 0.1, "f1")], ["error_rate", "latency"]) == []
