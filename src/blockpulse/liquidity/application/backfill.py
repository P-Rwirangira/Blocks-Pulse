"""Restartable historical pool backfill orchestration."""

from dataclasses import dataclass
from datetime import datetime

from blockpulse.domain.models import PoolDefinition, PoolEvent
from blockpulse.liquidity.application.collection import PoolCollectionService


@dataclass(frozen=True, slots=True)
class BackfillResult:
    """Summary of a bounded pool replay."""

    pool_id: str
    target_block: int
    final_block: int
    cycles: int
    events_seen: int
    events_inserted: int


class PoolBackfillService:
    """Replay confirmed pool ranges until a requested block is reached."""

    def __init__(self, collection: PoolCollectionService) -> None:
        self.collection = collection

    async def backfill(
        self, pool: PoolDefinition, target_block: int, observed_at: datetime
    ) -> BackfillResult:
        """Collect bounded ranges, stopping if the cursor cannot advance."""

        if target_block < pool.start_block:
            raise ValueError("target block cannot precede pool start block")

        cycles = 0
        events_seen = 0
        events_inserted = 0
        previous = await self.collection.cursors.get(pool.pool_id)
        while previous < target_block:
            events, inserted = await self.collection.collect_once(
                pool, observed_at, target_block=target_block
            )
            current = await self.collection.cursors.get(pool.pool_id)
            events_seen += len(events)
            events_inserted += inserted
            cycles += 1
            if current <= previous:
                break
            previous = current

        return BackfillResult(
            pool_id=pool.pool_id,
            target_block=target_block,
            final_block=previous,
            cycles=cycles,
            events_seen=events_seen,
            events_inserted=events_inserted,
        )
