import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from blockpulse.api import create_app
from blockpulse.domain import AnomalyScore, BinanceKline, HealthStatus, IncidentEvidence
from blockpulse.incidents import IncidentService
from blockpulse.infrastructure.database.repositories import (
    BinanceKlineRepository,
    Database,
    IncidentRepository,
)


def test_readiness_endpoint_checks_database() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    asyncio.run(database.create_schema())
    client = TestClient(create_app(database))
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    asyncio.run(database.close())


def test_metrics_endpoint_exposes_prometheus_text() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    asyncio.run(database.create_schema())
    client = TestClient(create_app(database))
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "blockpulse_http_requests_total" in response.text
    asyncio.run(database.close())


def test_binance_kline_route_returns_normalized_rows() -> None:
    async def seed(database: Database) -> None:
        await database.create_schema()
        async with database.sessions() as session:
            await BinanceKlineRepository(session).add_many(
                [
                    BinanceKline(
                        symbol="ETHUSDT", interval="1h",
                        open_time=datetime(2026, 11, 18, 0, tzinfo=UTC),
                        close_time=datetime(2026, 11, 18, 0, 59, 59, tzinfo=UTC),
                        open_price=2_000, high_price=2_010, low_price=1_990,
                        close_price=2_005, volume=100, quote_volume=200_000,
                        trade_count=10, taker_buy_volume=50,
                        taker_buy_quote_volume=100_000,
                        collected_at=datetime(2026, 11, 18, 1, tzinfo=UTC), raw_payload=[0],
                    )
                ]
            )

    database = Database("sqlite+aiosqlite:///:memory:")
    asyncio.run(seed(database))
    client = TestClient(create_app(database))
    response = client.get("/api/v1/markets/ETHUSDT/klines?interval=1h&limit=10")
    assert response.status_code == 200
    assert response.json()[0]["symbol"] == "ETHUSDT"
    asyncio.run(database.close())


def test_incident_api_exposes_detail_evidence_and_transition() -> None:
    async def seed(database: Database) -> str:
        await database.create_schema()
        score = AnomalyScore(
            anomaly_id="score-api-1", detector_name="ewma", detector_version="ewma-v1",
            entity_type="market", entity_id="ETHUSDT", chain_id=1,
            detected_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC), score=0.9,
            severity=HealthStatus.CRITICAL, drivers=["volatility"], feature_ids=["feature-api-1"],
        )
        incident = IncidentService().open_from_score(score)
        evidence = IncidentEvidence(
            evidence_id="evidence-api-1", incident_id=incident.incident_id,
            evidence_type="feature_snapshot", source_id="feature-api-1",
            observed_at=score.detected_at, summary="volatility elevated", payload={"value": 2.0},
        )
        async with database.sessions() as session:
            repository = IncidentRepository(session)
            await repository.add(incident)
            await repository.add_evidence(evidence)
        return incident.incident_id

    database = Database("sqlite+aiosqlite:///:memory:")
    incident_id = asyncio.run(seed(database))
    client = TestClient(create_app(database))
    assert client.get(f"/api/v1/incidents/{incident_id}").status_code == 200
    assert client.get(f"/api/v1/incidents/{incident_id}/evidence").json()[0]["source_id"] == "feature-api-1"
    transition = client.post(
        f"/api/v1/incidents/{incident_id}/transition",
        json={"status": "investigating", "actor": "test-operator", "reason": "triage"},
    )
    assert transition.status_code == 200
    assert client.get(f"/api/v1/incidents/{incident_id}/timeline").json()[0]["actor"] == "test-operator"
    asyncio.run(database.close())
