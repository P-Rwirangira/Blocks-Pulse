"""Deterministic metrics for normalized pool events."""

import math
from collections.abc import Sequence

from blockpulse.domain.models import PoolEvent, PoolMetric


def _liquidity_proxy(reserve0: float | None, reserve1: float | None) -> float | None:
    if reserve0 is None or reserve1 is None or reserve0 < 0 or reserve1 < 0:
        return None
    return math.sqrt(reserve0 * reserve1)


def calculate_pool_metric(
    pool_id: str, chain_id: int, events: Sequence[PoolEvent], window_minutes: int
) -> PoolMetric:
    """Aggregate swaps and syncs into a pool health metric."""

    if not events:
        raise ValueError("cannot calculate pool metrics without events")
    if any(event.pool_id != pool_id or event.chain_id != chain_id for event in events):
        raise ValueError("all events must belong to the requested pool")

    ordered = sorted(events, key=lambda event: (event.occurred_at, event.block_number, event.log_index))
    swaps = [event for event in ordered if event.event_type == "swap"]
    syncs = [event for event in ordered if event.event_type == "sync"]
    latest = syncs[-1] if syncs else None
    first = syncs[0] if syncs else None
    current_liquidity = _liquidity_proxy(
        latest.reserve0 if latest else None, latest.reserve1 if latest else None
    )
    initial_liquidity = _liquidity_proxy(
        first.reserve0 if first else None, first.reserve1 if first else None
    )
    change = None
    if initial_liquidity and current_liquidity is not None:
        change = ((current_liquidity - initial_liquidity) / initial_liquidity) * 100

    price = None
    if latest and latest.reserve0 and latest.reserve0 > 0 and latest.reserve1 is not None:
        price = latest.reserve1 / latest.reserve0

    return PoolMetric(
        pool_id=pool_id,
        chain_id=chain_id,
        measured_at=ordered[-1].occurred_at,
        window_minutes=window_minutes,
        swap_count=len(swaps),
        volume_token0=sum(abs(event.amount0 or 0) for event in swaps),
        volume_token1=sum(abs(event.amount1 or 0) for event in swaps),
        latest_reserve0=latest.reserve0 if latest else None,
        latest_reserve1=latest.reserve1 if latest else None,
        liquidity_change_pct=change,
        price_token1_per_token0=price,
    )
