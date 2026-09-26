"""Application services for pool metrics and event inspection."""

from blockpulse.domain import PoolDefinition, PoolEvent, PoolMetric
from blockpulse.pool_monitoring import calculate_pool_metric
from blockpulse.v3_monitoring import calculate_v3_metric
from blockpulse.storage import PoolEventRepository


class PoolService:
    """Coordinate pool event reads and pure metric calculations."""

    def __init__(self, repository: PoolEventRepository) -> None:
        self.repository = repository

    async def events(self, pool_id: str, limit: int = 500) -> list[PoolEvent]:
        rows = await self.repository.recent(pool_id, limit)
        return [
            PoolEvent(
                event_id=row.event_id,
                pool_id=row.pool_id,
                chain_id=row.chain_id,
                block_number=row.block_number,
                block_hash=row.block_hash,
                transaction_hash=row.transaction_hash,
                log_index=row.log_index,
                event_type=row.event_type,
                occurred_at=row.occurred_at,
                amount0=row.amount0,
                amount1=row.amount1,
                reserve0=row.reserve0,
                reserve1=row.reserve1,
                sqrt_price_x96=(int(row.sqrt_price_x96) if row.sqrt_price_x96 is not None else None),
                tick=row.tick,
                active_liquidity=(int(row.active_liquidity) if row.active_liquidity is not None else None),
                tick_lower=row.tick_lower,
                tick_upper=row.tick_upper,
            )
            for row in rows
        ]

    async def current(self, pool: PoolDefinition, window_minutes: int) -> PoolMetric:
        events = await self.events(pool.pool_id)
        if not events:
            raise LookupError(f"no events found for pool {pool.pool_id}")
        if pool.version.lower() == "v3":
            return calculate_v3_metric(pool, events, window_minutes)
        return calculate_pool_metric(pool.pool_id, pool.chain_id, events, window_minutes)
