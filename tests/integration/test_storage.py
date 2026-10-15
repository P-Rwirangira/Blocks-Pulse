import asyncio
from datetime import UTC, datetime

from blockpulse.domain import FeatureSnapshot, HealthMetric, HealthStatus, RpcObservation
from blockpulse.storage import (
    Database,
    HealthMetricRepository,
    FeatureRepository,
    ObservationQualityRepository,
    ObservationRepository,
)
from blockpulse.chain_health.application.quality import ObservationQualityReport


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
            raw_payload={"result": "0x7b"},
            latest_block_hash="0xabc",
            latest_parent_hash="0xdef",
        )
        retry = observation.model_copy(update={"attempt": 1, "success": False})
        async with database.sessions() as session:
            repository = ObservationRepository(session)
            assert await repository.add_many([observation]) == 1
            assert await repository.add_many([retry]) == 1
            assert await repository.add_many([observation]) == 0
            rows = await repository.recent(8453)
            assert len(rows) == 2
            assert rows[0].latest_block_number == 123
            assert rows[0].raw_payload == {"result": "0x7b"}
            assert rows[0].latest_block_hash == "0xabc"
        await database.close()

    asyncio.run(scenario())


def test_metrics_and_quality_reports_are_idempotent() -> None:
    async def scenario() -> None:
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_schema()
        measured_at = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
        metric = HealthMetric(
            chain_id=8453,
            measured_at=measured_at,
            window_minutes=15,
            request_count=2,
            error_rate=0,
            p95_latency_ms=100,
            latest_block_number=123,
            status=HealthStatus.HEALTHY,
        )
        report = ObservationQualityReport(measured_at, 2, False, 0, 0, ())
        async with database.sessions() as session:
            metrics = HealthMetricRepository(session)
            quality = ObservationQualityRepository(session)
            assert await metrics.add_many([metric, metric]) == 1
            assert len(await metrics.recent(8453)) == 1
            assert await quality.add(report) is True
            assert await quality.add(report) is False
        await database.close()

    asyncio.run(scenario())


def test_feature_snapshots_are_idempotent_and_traceable() -> None:
    async def scenario() -> None:
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_schema()
        feature = FeatureSnapshot(
            feature_id="feature-1",
            feature_name="rpc_error_rate",
            feature_version="rpc-v1",
            entity_type="chain",
            entity_id="8453",
            chain_id=8453,
            measured_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            window_minutes=15,
            value=0.1,
            source_observation_ids=["observation-1"],
        )
        async with database.sessions() as session:
            repository = FeatureRepository(session)
            assert await repository.add_many([feature, feature]) == 1
            rows = await repository.recent("8453")
            assert rows[0].source_observation_ids == ["observation-1"]
        await database.close()

    asyncio.run(scenario())
