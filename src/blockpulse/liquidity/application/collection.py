"""Confirmed block-range collection for configured pools."""

from datetime import datetime

from blockpulse.domain.models import PoolDefinition, PoolEvent
from blockpulse.infrastructure.database.repositories import PoolCursorRepository, PoolEventRepository
from blockpulse.liquidity.adapters.uniswap.v2.decoder import PoolLogCollector
from blockpulse.liquidity.adapters.uniswap.v3.decoder import V3PoolLogCollector


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
        await self.cursors.advance(pool.pool_id, confirmed_to)
        return events, inserted
