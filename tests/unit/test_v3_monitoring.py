from datetime import UTC, datetime

from blockpulse.domain import PoolDefinition, PoolEvent
from blockpulse.v3_monitoring import calculate_v3_metric


POOL = PoolDefinition(
    pool_id="base-v3-weth-usdc",
    chain_id=8453,
    address="0xpool",
    version="v3",
    token0_symbol="WETH",
    token1_symbol="USDC",
    token0_decimals=18,
    token1_decimals=6,
)


def test_v3_metric_uses_sqrt_price_and_active_liquidity() -> None:
    events = [
        PoolEvent(
            event_id="swap",
            pool_id=POOL.pool_id,
            chain_id=POOL.chain_id,
            block_number=1,
            block_hash="0x1",
            transaction_hash="0xtx",
            log_index=0,
            event_type="swap",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
            amount0=-10**18,
            amount1=2_000_000,
            sqrt_price_x96=2**96,
            tick=-10,
            active_liquidity=500_000,
        )
    ]

    metric = calculate_v3_metric(POOL, events, 5)

    assert metric.price_token1_per_token0 == 10**12
    assert metric.latest_tick == -10
    assert metric.active_liquidity == 500_000
    assert metric.volume_token0 == 1
    assert metric.volume_token1 == 2

