"""Feature generation for RPC and chain-health observations."""

from collections import defaultdict
from collections.abc import Sequence

from blockpulse.chain_health.application.metrics import calculate_rpc_health
from blockpulse.domain.models import FeatureSnapshot, RpcObservation
from blockpulse.shared.identity import feature_reference, observation_reference


RPC_FEATURE_VERSION = "rpc-v1"


def build_rpc_features(
    observations: Sequence[RpcObservation],
    window_minutes: int,
    feature_version: str = RPC_FEATURE_VERSION,
) -> list[FeatureSnapshot]:
    """Build explainable chain-health features from one or more chains."""

    if not observations:
        raise ValueError("cannot build features without observations")
    grouped: dict[int, list[RpcObservation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.chain_id].append(observation)

    features: list[FeatureSnapshot] = []
    for chain_id, values in sorted(grouped.items()):
        metric = calculate_rpc_health(values, window_minutes)
        source_ids = [observation_reference(item) for item in values]
        values_by_name = {
            "rpc_error_rate": metric.error_rate,
            "rpc_p95_latency_ms": metric.p95_latency_ms,
            "rpc_block_disagreement": float(metric.block_disagreement),
        }
        for feature_name, value in values_by_name.items():
            entity_id = str(chain_id)
            measured_at = metric.measured_at.isoformat()
            features.append(
                FeatureSnapshot(
                    feature_id=feature_reference(
                        feature_name, feature_version, entity_id, measured_at, window_minutes
                    ),
                    feature_name=feature_name,
                    feature_version=feature_version,
                    entity_type="chain",
                    entity_id=entity_id,
                    chain_id=chain_id,
                    measured_at=metric.measured_at,
                    window_minutes=window_minutes,
                    value=value,
                    source_observation_ids=source_ids,
                )
            )
    return features
