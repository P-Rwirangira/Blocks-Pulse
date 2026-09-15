import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from blockpulse.api import create_app
from blockpulse.domain import RpcObservation
from blockpulse.storage import Database, ObservationRepository


def test_health_endpoint_returns_metric() -> None:
    async def seed(database: Database) -> None:
        await database.create_schema()
        async with database.sessions() as session:
            await ObservationRepository(session).add_many(
                [
                    RpcObservation(
                        endpoint_name="base-a",
                        chain_id=8453,
                        observed_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
                        latency_ms=100,
                        success=True,
                        latest_block_number=100,
                    ),
                    RpcObservation(
                        endpoint_name="eth-a",
                        chain_id=1,
                        observed_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
                        latency_ms=200,
                        success=True,
                        latest_block_number=200,
                    ),
                ]
            )

    database = Database("sqlite+aiosqlite:///:memory:")
    asyncio.run(seed(database))
    client = TestClient(create_app(database))

    response = client.get("/api/v1/chains/8453/health")

    assert response.status_code == 200
    assert response.json()["chain_id"] == 8453
    assert response.json()["status"] == "healthy"
    asyncio.run(database.close())


def test_overview_returns_observed_chains() -> None:
    async def seed(database: Database) -> None:
        await database.create_schema()
        async with database.sessions() as session:
            await ObservationRepository(session).add_many(
                [
                    RpcObservation(
                        endpoint_name="base-a",
                        chain_id=8453,
                        observed_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
                        latency_ms=100,
                        success=True,
                        latest_block_number=100,
                    ),
                    RpcObservation(
                        endpoint_name="eth-a",
                        chain_id=1,
                        observed_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
                        latency_ms=200,
                        success=True,
                        latest_block_number=200,
                    ),
                ]
            )

    database = Database("sqlite+aiosqlite:///:memory:")
    asyncio.run(seed(database))
    client = TestClient(create_app(database))

    response = client.get("/api/v1/overview")

    assert response.status_code == 200
    body = response.json()
    assert {item["name"] for item in body["chains"]} == {"ethereum", "base"}
    assert body["healthiest_chain"] in {"ethereum", "base"}
    asyncio.run(database.close())


def test_health_endpoint_returns_not_found_without_observations() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    asyncio.run(database.create_schema())
    client = TestClient(create_app(database))

    response = client.get("/api/v1/chains/8453/health")

    assert response.status_code == 404
    asyncio.run(database.close())
