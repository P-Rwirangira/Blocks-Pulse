import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from blockpulse.api import create_app
from blockpulse.domain import AnomalyScore, HealthStatus, IncidentEvidence, RpcObservation
from blockpulse.incidents import IncidentService
from blockpulse.storage import Database, IncidentRepository, ObservationRepository


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


def test_endpoint_health_route_returns_provider_scores() -> None:
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
                        endpoint_name="base-b",
                        chain_id=8453,
                        observed_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
                        latency_ms=200,
                        success=False,
                        error_type="timeout",
                    ),
                ]
            )

    database = Database("sqlite+aiosqlite:///:memory:")
    asyncio.run(seed(database))
    client = TestClient(create_app(database))

    response = client.get("/api/v1/chains/8453/endpoints/health")

    assert response.status_code == 200
    assert {item["endpoint_name"] for item in response.json()} == {"base-a", "base-b"}
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


def test_incident_api_exposes_detail_evidence_timeline_and_transition() -> None:
    async def seed(database: Database) -> str:
        await database.create_schema()
        score = AnomalyScore(
            anomaly_id="score-api-1", detector_name="ewma", detector_version="ewma-v1",
            entity_type="chain", entity_id="8453", chain_id=8453,
            detected_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC), score=0.9,
            severity=HealthStatus.CRITICAL, drivers=["rpc_latency"], feature_ids=["feature-api-1"],
        )
        incident = IncidentService().open_from_score(score)
        evidence = IncidentEvidence(
            evidence_id="evidence-api-1", incident_id=incident.incident_id,
            evidence_type="feature_snapshot", source_id="feature-api-1",
            observed_at=score.detected_at, summary="latency elevated", payload={"value": 2000.0},
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
    assert client.get("/api/v1/incidents?chain_id=8453").json()[0]["incident_id"] == incident_id
    assert client.get(f"/api/v1/incidents/{incident_id}/evidence").json()[0]["source_id"] == "feature-api-1"
    transition = client.post(
        f"/api/v1/incidents/{incident_id}/transition",
        json={"status": "investigating", "actor": "test-operator", "reason": "triage"},
    )
    assert transition.status_code == 200
    assert transition.json()["status"] == "investigating"
    assert client.get(f"/api/v1/incidents/{incident_id}/timeline").json()[0]["actor"] == "test-operator"
    assert client.post(
        f"/api/v1/incidents/{incident_id}/transition",
        json={"status": "resolved", "actor": "test-operator"},
    ).status_code == 200
    assert client.post(
        f"/api/v1/incidents/{incident_id}/transition",
        json={"status": "investigating", "actor": "test-operator"},
    ).status_code == 409
    asyncio.run(database.close())
