"""Confirmed block-range collection for configured pools."""

from datetime import datetime

from blockpulse.domain.models import PoolDefinition, PoolEvent
from blockpulse.infrastructure.database.repositories import PoolCursorRepository, PoolEventRepository
from blockpulse.liquidity.adapters.uniswap.v2.decoder import PoolLogCollector
from blockpulse.liquidity.adapters.uniswap.v3.decoder import V3PoolLogCollector
from typing import Protocol


class PoolMetricsSink(Protocol):
    """Application-facing port for pool collection telemetry."""

    def observe_pool_event(self, pool_id: str, event_type: str) -> None:
        """Record one normalized pool event."""


class PoolCollectionService:
    """Collect one confirmed range and advance its replay cursor."""

    def __init__(
        self,
        provider: object,
        events: PoolEventRepository,
        cursors: PoolCursorRepository,
        confirmations: int = 2,
        metrics: PoolMetricsSink | None = None,
        max_range_blocks: int = 10_000,
    ) -> None:
        if max_range_blocks <= 0:
            raise ValueError("max_range_blocks must be positive")
        self.provider = provider
        self.events = events
        self.cursors = cursors
        self.confirmations = confirmations
        self.metrics = metrics
        self.max_range_blocks = max_range_blocks

    async def collect_once(
        self, pool: PoolDefinition, observed_at: datetime, target_block: int | None = None
    ) -> tuple[list[PoolEvent], int]:
        """Collect the next confirmed range for a pool."""

        head = await self.provider.observe_latest_block(observed_at)
        if not head.success or head.latest_block_number is None:
            return [], 0
        confirmed_to = head.latest_block_number - self.confirmations
        if target_block is not None:
            if target_block < pool.start_block:
                raise ValueError("target block cannot precede pool start block")
            confirmed_to = min(confirmed_to, target_block)
        last_processed = await self.cursors.get(pool.pool_id)
        from_block = max(pool.start_block, last_processed + 1)
        confirmed_to = min(confirmed_to, from_block + self.max_range_blocks - 1)
        if confirmed_to < from_block:
            return [], 0

        if pool.version.lower() == "v3":
            events = await V3PoolLogCollector(self.provider).collect(
                pool, from_block, confirmed_to, observed_at
            )
        else:
            events = await PoolLogCollector(self.provider).collect_v2(
                pool, from_block, confirmed_to, observed_at
            )
        inserted = await self.events.add_many(events)
        if self.metrics is not None:
            for event in events:
                self.metrics.observe_pool_event(event.pool_id, event.event_type)
        await self.cursors.advance(pool.pool_id, confirmed_to)
        return events, inserted
