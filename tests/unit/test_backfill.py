import asyncio
from datetime import UTC, datetime

import pytest

from blockpulse.domain import PoolDefinition
from blockpulse.infrastructure.database.repositories import (
    Database,
    PoolCursorRepository,
    PoolEventRepository,
)
from blockpulse.liquidity.application.backfill import PoolBackfillService
from blockpulse.liquidity.application.collection import PoolCollectionService
from tests.integration.test_pool_collection import FakeProvider


POOL = PoolDefinition(
    pool_id="base-weth-usdc",
    chain_id=8453,
    address="0xpool",
    token0_symbol="WETH",
    token1_symbol="USDC",
    token0_decimals=18,
    token1_decimals=6,
    start_block=100,
)


def test_backfill_stops_at_bounded_target() -> None:
    async def scenario() -> None:
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_schema()
        async with database.sessions() as session:
            collection = PoolCollectionService(
                FakeProvider(),
                PoolEventRepository(session),
                PoolCursorRepository(session),
                confirmations=2,
            )
            result = await PoolBackfillService(collection).backfill(
                POOL, target_block=103, observed_at=datetime.now(UTC)
            )
            assert result.final_block == 103
            assert result.cycles == 1
            assert result.events_seen == 1
        await database.close()

    asyncio.run(scenario())


def test_backfill_rejects_target_before_pool_start() -> None:
    async def scenario() -> None:
        with pytest.raises(ValueError, match="precede"):
            await PoolBackfillService(object()).backfill(POOL, 99, datetime.now(UTC))

    asyncio.run(scenario())
