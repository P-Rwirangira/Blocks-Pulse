from datetime import UTC, datetime

from blockpulse.domain import FeatureSnapshot
from blockpulse.liquidity.application.cross_chain_features import build_cross_chain_price_features


def price(pool_id: str, chain_id: int, value: float) -> FeatureSnapshot:
    return FeatureSnapshot(
        feature_id=f"{pool_id}-price",
        feature_name="pool_price_token1_per_token0",
        feature_version="pool-v1",
        entity_type="pool",
        entity_id=pool_id,
        chain_id=chain_id,
        measured_at=datetime(2026, 10, 14, 9, 0, tzinfo=UTC),
        window_minutes=15,
        value=value,
        source_observation_ids=[f"{pool_id}-event"],
    )


def test_cross_chain_features_measure_price_dispersion() -> None:
    features = build_cross_chain_price_features(
        [price("base-pool", 8453, 3000), price("eth-pool", 1, 3030)],
        {"base-pool": "WETH/USDC", "eth-pool": "WETH/USDC"},
    )

    assert len(features) == 2
    dispersion = next(
        item for item in features if item.feature_name == "cross_chain_price_dispersion_pct"
    )
    assert dispersion.chain_id == 0
    assert round(dispersion.value, 2) == 1.0
