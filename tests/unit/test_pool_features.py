from datetime import UTC, datetime

from blockpulse.domain import PoolDefinition, PoolEvent
from blockpulse.liquidity.application.features import build_pool_features


def test_pool_features_include_volume_and_price() -> None:
    pool = PoolDefinition(
        pool_id="base-weth-usdc",
        chain_id=8453,
        address="0xpool",
        token0_symbol="WETH",
        token1_symbol="USDC",
        token0_decimals=18,
        token1_decimals=6,
    )
    event = PoolEvent(
        event_id="event-1",
        pool_id=pool.pool_id,
        chain_id=pool.chain_id,
        block_number=100,
        block_hash="0xblock",
        transaction_hash="0xtx",
        log_index=0,
        event_type="swap",
        occurred_at=datetime(2026, 10, 14, 9, 0, tzinfo=UTC),
        amount0=-2,
        amount1=3000,
        reserve0=10,
        reserve1=15000,
    )

    sync = event.model_copy(
        update={
            "event_id": "event-2",
            "event_type": "sync",
            "amount0": None,
            "amount1": None,
        }
    )
    features = build_pool_features(pool, [event, sync], window_minutes=15)

    names = {feature.feature_name for feature in features}
    assert {"pool_swap_count", "pool_volume_token0", "pool_price_token1_per_token0"} <= names
    assert all(feature.source_observation_ids == ["event-1", "event-2"] for feature in features)
