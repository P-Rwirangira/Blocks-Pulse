"""Monitoring metrics for concentrated-liquidity V3 pools."""

from collections.abc import Sequence

from blockpulse.domain.models import PoolDefinition, PoolEvent, PoolMetric
from blockpulse.liquidity.adapters.uniswap.v3.state import price_token1_per_token0


def calculate_v3_metric(
    pool: PoolDefinition, events: Sequence[PoolEvent], window_minutes: int
) -> PoolMetric:
    """Aggregate V3 events without pretending that active liquidity is reserves."""

    if not events:
        raise ValueError("cannot calculate V3 metrics without events")
    ordered = sorted(events, key=lambda event: (event.occurred_at, event.block_number, event.log_index))
    swaps = [event for event in ordered if event.event_type == "swap"]
    state = next(
        (event for event in reversed(ordered) if event.sqrt_price_x96 is not None), None
    )
    liquidity = state.active_liquidity if state else None
    price = (
        price_token1_per_token0(
            state.sqrt_price_x96, pool.token0_decimals, pool.token1_decimals
        )
        if state and state.sqrt_price_x96 is not None
        else None
    )
    minted = sum(event.active_liquidity or 0 for event in ordered if event.event_type == "mint")
    burned = sum(event.active_liquidity or 0 for event in ordered if event.event_type == "burn")
    liquidity_change = ((minted - burned) / minted * 100) if minted else None
    return PoolMetric(
        pool_id=pool.pool_id,
        chain_id=pool.chain_id,
        measured_at=ordered[-1].occurred_at,
        window_minutes=window_minutes,
        swap_count=len(swaps),
        volume_token0=sum(abs(event.amount0 or 0) / 10**pool.token0_decimals for event in swaps),
        volume_token1=sum(abs(event.amount1 or 0) / 10**pool.token1_decimals for event in swaps),
        liquidity_change_pct=liquidity_change,
        price_token1_per_token0=price,
        latest_tick=state.tick if state else None,
        latest_sqrt_price_x96=state.sqrt_price_x96 if state else None,
        active_liquidity=liquidity,
    )
