import asyncio
from datetime import UTC, datetime

from blockpulse.domain import (
    AnomalyScore,
    FeatureSnapshot,
    HealthMetric,
    HealthStatus,
    IncidentEvidence,
    ModelEvaluation,
    RpcObservation,
)
from blockpulse.storage import (
    Database,
    HealthMetricRepository,
    FeatureRepository,
    AnomalyRepository,
    EvaluationRepository,
    IncidentRepository,
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


def test_anomaly_scores_are_idempotent_and_traceable() -> None:
    async def scenario() -> None:
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_schema()
        anomaly = AnomalyScore(
            anomaly_id="anomaly-1",
            detector_name="robust_mad",
            detector_version="mad-v1",
            entity_type="chain",
            entity_id="8453",
            chain_id=8453,
            detected_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            score=0.8,
            severity=HealthStatus.CRITICAL,
            drivers=["rpc_error_rate"],
            feature_ids=["feature-1"],
        )
        async with database.sessions() as session:
            repository = AnomalyRepository(session)
            assert await repository.add_many([anomaly, anomaly]) == 1
            assert (await repository.recent("8453"))[0].feature_ids == ["feature-1"]
        await database.close()

    asyncio.run(scenario())


def test_model_evaluations_are_idempotent() -> None:
    async def scenario() -> None:
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_schema()
        evaluation = ModelEvaluation(
            run_id="run-1",
            detector_name="robust_mad",
            detector_version="mad-v1",
            feature_version="rpc-v1",
            evaluated_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            train_count=10,
            validation_count=2,
            test_count=3,
            precision=0.8,
            recall=0.7,
            false_positive_rate=0.1,
            parameters={"threshold": 3.5},
        )
        async with database.sessions() as session:
            repository = EvaluationRepository(session)
            assert await repository.add(evaluation) is True
            assert await repository.add(evaluation) is False
        await database.close()

    asyncio.run(scenario())


def test_incidents_evidence_and_history_are_idempotent() -> None:
    async def scenario() -> None:
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_schema()
        score = AnomalyScore(
            anomaly_id="score-1",
            detector_name="ewma",
            detector_version="ewma-v1",
            entity_type="chain",
            entity_id="8453",
            chain_id=8453,
            detected_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            score=0.8,
            severity=HealthStatus.WARNING,
            drivers=["rpc_latency"],
            feature_ids=["feature-1"],
        )
        from blockpulse.incidents import IncidentService

        incident = IncidentService().open_from_score(score)
        evidence = IncidentEvidence(
            evidence_id="evidence-1",
            incident_id=incident.incident_id,
            evidence_type="feature_snapshot",
            source_id="feature-1",
            observed_at=score.detected_at,
            summary="RPC latency exceeded baseline",
            payload={"value": 2000.0},
        )
        async with database.sessions() as session:
            repository = IncidentRepository(session)
            assert await repository.add(incident) is True
            assert await repository.add(incident) is False
            assert await repository.add_evidence(evidence) is True
            assert await repository.add_evidence(evidence) is False
            rows = await repository.recent(8453)
            assert rows[0].fingerprint == incident.fingerprint
            assert (await repository.evidence(incident.incident_id))[0].source_id == "feature-1"
        await database.close()

    asyncio.run(scenario())
