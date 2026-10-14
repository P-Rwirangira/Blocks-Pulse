"""Feature generation for normalized pool events."""

from collections.abc import Sequence

from blockpulse.domain.models import FeatureSnapshot, PoolDefinition, PoolEvent, PoolMetric
from blockpulse.liquidity.application.metrics import calculate_pool_metric
from blockpulse.liquidity.application.v3_metrics import calculate_v3_metric
from blockpulse.shared.identity import feature_reference


POOL_FEATURE_VERSION = "pool-v1"


def build_pool_features(
    pool: PoolDefinition,
    events: Sequence[PoolEvent],
    window_minutes: int,
    feature_version: str = POOL_FEATURE_VERSION,
) -> list[FeatureSnapshot]:
    """Build normalized volume, price, and liquidity features for one pool."""

    if not events:
        raise ValueError("cannot build pool features without events")
    metric: PoolMetric = (
        calculate_v3_metric(pool, events, window_minutes)
        if pool.version.lower() == "v3"
        else calculate_pool_metric(pool.pool_id, pool.chain_id, events, window_minutes)
    )
    values = {
        "pool_swap_count": float(metric.swap_count),
        "pool_volume_token0": metric.volume_token0,
        "pool_volume_token1": metric.volume_token1,
    }
    optional_values = {
        "pool_price_token1_per_token0": metric.price_token1_per_token0,
        "pool_liquidity_change_pct": metric.liquidity_change_pct,
        "pool_latest_tick": float(metric.latest_tick) if metric.latest_tick is not None else None,
        "pool_active_liquidity": (
            float(metric.active_liquidity) if metric.active_liquidity is not None else None
        ),
    }
    values.update({name: value for name, value in optional_values.items() if value is not None})
    source_ids = [event.event_id for event in events]
    measured_at = metric.measured_at.isoformat()
    return [
        FeatureSnapshot(
            feature_id=feature_reference(
                feature_name, feature_version, pool.pool_id, measured_at, window_minutes
            ),
            feature_name=feature_name,
            feature_version=feature_version,
            entity_type="pool",
            entity_id=pool.pool_id,
            chain_id=pool.chain_id,
            measured_at=metric.measured_at,
            window_minutes=window_minutes,
            value=value,
            source_observation_ids=source_ids,
        )
        for feature_name, value in values.items()
    ]
