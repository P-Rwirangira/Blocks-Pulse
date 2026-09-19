import asyncio
from datetime import UTC, datetime

from blockpulse.domain import PoolEvent
from blockpulse.storage import Database, PoolEventRepository


def test_pool_events_are_idempotent() -> None:
    async def scenario() -> None:
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_schema()
        event = PoolEvent(
            event_id="8453:0xtx:1",
            pool_id="base-weth-usdc",
            chain_id=8453,
            block_number=100,
            block_hash="0xblock",
            transaction_hash="0xtx",
            log_index=1,
            event_type="sync",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
            reserve0=2,
            reserve1=3,
        )
        async with database.sessions() as session:
            repository = PoolEventRepository(session)
            assert await repository.add_many([event]) == 1
            assert await repository.add_many([event]) == 0
            rows = await repository.recent("base-weth-usdc")
            assert rows[0].reserve0 == 2
        await database.close()

    asyncio.run(scenario())

