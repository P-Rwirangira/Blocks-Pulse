import asyncio
from datetime import UTC, datetime

from blockpulse.domain import RpcObservation
from blockpulse.storage import Database, ObservationRepository


def test_observations_are_idempotent() -> None:
    async def scenario() -> None:
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_schema()
        observed_at = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
        observation = RpcObservation(
            endpoint_name="base-a",
            chain_id=8453,
            observed_at=observed_at,
            latency_ms=100,
            success=True,
            latest_block_number=123,
        )
        async with database.sessions() as session:
            repository = ObservationRepository(session)
            assert await repository.add_many([observation]) == 1
            assert await repository.add_many([observation]) == 0
            rows = await repository.recent(8453)
            assert len(rows) == 1
            assert rows[0].latest_block_number == 123
        await database.close()

    asyncio.run(scenario())

