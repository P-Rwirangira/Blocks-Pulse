from datetime import UTC, datetime, timedelta

from blockpulse.domain import PoolEvent
from blockpulse.pool_monitoring import calculate_pool_metric


def event(event_id: str, event_type: str, at: datetime, **values: float) -> PoolEvent:
    return PoolEvent(
        event_id=event_id,
        pool_id="base-weth-usdc",
        chain_id=8453,
        block_number=100,
        block_hash="0xblock",
        transaction_hash=event_id,
        log_index=1,
        event_type=event_type,
        occurred_at=at,
        **values,
    )


def test_pool_metric_calculates_volume_price_and_liquidity_change() -> None:
    start = datetime(2026, 9, 1, tzinfo=UTC)
    metric = calculate_pool_metric(
        "base-weth-usdc",
        8453,
        [
            event("sync-1", "sync", start, reserve0=2, reserve1=3_000),
            event("swap-1", "swap", start + timedelta(minutes=1), amount0=1, amount1=-100),
            event("sync-2", "sync", start + timedelta(minutes=2), reserve0=1, reserve1=3_200),
        ],
        window_minutes=5,
    )

    assert metric.swap_count == 1
    assert metric.volume_token0 == 1
    assert metric.volume_token1 == 100
    assert metric.price_token1_per_token0 == 3_200
    assert metric.liquidity_change_pct is not None

