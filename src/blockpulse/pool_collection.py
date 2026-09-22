"""Confirmed block-range collection for configured pools."""

from datetime import datetime

from blockpulse.domain import PoolDefinition, PoolEvent
from blockpulse.pool_events import PoolLogCollector
from blockpulse.rpc import RawLog
from blockpulse.storage import PoolCursorRepository, PoolEventRepository


class PoolCollectionService:
    """Collect one confirmed range and advance its replay cursor."""

    def __init__(
        self,
        provider: object,
        events: PoolEventRepository,
        cursors: PoolCursorRepository,
        confirmations: int = 2,
    ) -> None:
        self.provider = provider
        self.events = events
        self.cursors = cursors
        self.confirmations = confirmations

    async def collect_once(
        self, pool: PoolDefinition, observed_at: datetime
    ) -> tuple[list[PoolEvent], int]:
        """Collect the next confirmed range for a pool."""

        head = await self.provider.observe_latest_block(observed_at)
        if not head.success or head.latest_block_number is None:
            return [], 0
        confirmed_to = head.latest_block_number - self.confirmations
        last_processed = await self.cursors.get(pool.pool_id)
        from_block = max(pool.start_block, last_processed + 1)
        if confirmed_to < from_block:
            return [], 0

        events = await PoolLogCollector(self.provider).collect_v2(
            pool, from_block, confirmed_to, observed_at
        )
        inserted = await self.events.add_many(events)
        await self.cursors.advance(pool.pool_id, confirmed_to)
        return events, inserted

