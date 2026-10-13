from datetime import UTC, datetime

from blockpulse.chain_health.application.features import build_rpc_features
from blockpulse.domain import RpcObservation


def test_rpc_features_are_versioned_and_traceable() -> None:
    observations = [
        RpcObservation(
            endpoint_name="base-a",
            chain_id=8453,
            observed_at=datetime(2026, 10, 13, 9, 0, tzinfo=UTC),
            latency_ms=100,
            success=True,
            latest_block_number=100,
        ),
        RpcObservation(
            endpoint_name="base-b",
            chain_id=8453,
            observed_at=datetime(2026, 10, 13, 9, 0, tzinfo=UTC),
            latency_ms=200,
            success=False,
            latest_block_number=None,
            error_type="timeout",
        ),
    ]

    features = build_rpc_features(observations, window_minutes=15)

    assert {feature.feature_name for feature in features} == {
        "rpc_error_rate",
        "rpc_p95_latency_ms",
        "rpc_block_disagreement",
    }
    assert all(feature.feature_version == "rpc-v1" for feature in features)
    assert all(len(feature.source_observation_ids) == 2 for feature in features)
    assert next(feature.value for feature in features if feature.feature_name == "rpc_error_rate") == 0.5
