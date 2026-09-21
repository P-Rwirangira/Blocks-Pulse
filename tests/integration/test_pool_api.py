import asyncio
import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from blockpulse.api import create_app
from blockpulse.config import get_settings
from blockpulse.domain import PoolEvent
from blockpulse.storage import Database, PoolEventRepository


def test_pool_metrics_endpoint_returns_metric(monkeypatch) -> None:
    monkeypatch.setenv(
        "BLOCKPULSE_POOLS_JSON",
        json.dumps(
            [
                {
                    "pool_id": "base-weth-usdc",
                    "chain_id": 8453,
                    "address": "0xpool",
                    "token0_symbol": "WETH",
                    "token1_symbol": "USDC",
                    "token0_decimals": 18,
                    "token1_decimals": 6,
                }
            ]
        ),
    )
    get_settings.cache_clear()

    async def seed(database: Database) -> None:
        await database.create_schema()
        async with database.sessions() as session:
            await PoolEventRepository(session).add_many(
                [
                    PoolEvent(
                        event_id="sync-1",
                        pool_id="base-weth-usdc",
                        chain_id=8453,
                        block_number=100,
                        block_hash="0xblock",
                        transaction_hash="0xtx",
                        log_index=1,
                        event_type="sync",
                        occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
                        reserve0=2,
                        reserve1=3_000,
                    )
                ]
            )

    database = Database("sqlite+aiosqlite:///:memory:")
    asyncio.run(seed(database))
    client = TestClient(create_app(database))

    response = client.get("/api/v1/pools/base-weth-usdc/metrics")

    assert response.status_code == 200
    assert response.json()["swap_count"] == 0
    assert response.json()["latest_reserve1"] == 3000
    asyncio.run(database.close())
    get_settings.cache_clear()

