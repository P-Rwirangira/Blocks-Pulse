import asyncio
from datetime import UTC, datetime

import pytest

from blockpulse.domain import PoolDefinition, RpcObservation
from blockpulse.chain_health.application.backfill import HistoricalHealthProjection
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


def test_historical_health_projection_groups_utc_windows() -> None:
    first = RpcObservation(
        endpoint_name="base-a",
        chain_id=8453,
        observed_at=datetime(2026, 10, 10, 9, 1, tzinfo=UTC),
        latency_ms=100,
        success=True,
        latest_block_number=100,
    )
    second = first.model_copy(
        update={
            "observed_at": datetime(2026, 10, 10, 9, 16, tzinfo=UTC),
            "latest_block_number": 110,
        }
    )

    metrics = HistoricalHealthProjection().build([first, second], window_minutes=15)

    assert len(metrics) == 2
    assert [metric.latest_block_number for metric in metrics] == [100, 110]
