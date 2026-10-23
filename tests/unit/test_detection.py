from datetime import UTC, datetime

from blockpulse.detectors import detect_rpc_anomaly
from blockpulse.domain import AnomalyScore, FeatureSnapshot, HealthMetric, HealthStatus, IncidentStatus
from blockpulse.incidents import IncidentService
from blockpulse.incidents.application.evidence import EvidencePackageBuilder


def test_detector_returns_drivers_for_latency_anomaly() -> None:
    metric = HealthMetric(
        chain_id=8453,
        measured_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        window_minutes=15,
        request_count=10,
        error_rate=0.0,
        p95_latency_ms=2_000,
        block_disagreement=0,
        status=HealthStatus.WARNING,
    )

    anomaly = detect_rpc_anomaly(metric, baseline_latency_ms=200, baseline_error_rate=0.0)

    assert anomaly is not None
    assert anomaly.status is HealthStatus.WARNING
    assert anomaly.drivers == ["rpc_latency"]
    assert anomaly.score == 1.0


def test_incident_is_reproducible_and_open() -> None:
    metric = HealthMetric(
        chain_id=8453,
        measured_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        window_minutes=15,
        request_count=10,
        error_rate=0.2,
        p95_latency_ms=2_000,
        block_disagreement=2,
        status=HealthStatus.WARNING,
    )
    anomaly = detect_rpc_anomaly(metric, baseline_latency_ms=200, baseline_error_rate=0.01)
    assert anomaly is not None

    incident = IncidentService().open_from_anomaly(anomaly)
    assert incident.status is IncidentStatus.OPEN
    assert incident.anomaly_event_id == anomaly.event_id
    assert incident.evidence_ids == [anomaly.event_id]


def test_score_incident_is_grouped_and_transition_is_audited() -> None:
    score = AnomalyScore(
        anomaly_id="score-1",
        detector_name="ewma",
        detector_version="ewma-v1",
        entity_type="chain",
        entity_id="8453",
        chain_id=8453,
        detected_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        score=0.9,
        severity=HealthStatus.CRITICAL,
        drivers=["rpc_latency", "rpc_error_rate"],
        feature_ids=["feature-1", "feature-2"],
    )
    service = IncidentService()
    incident = service.open_from_score(score)
    same_group = service.open_from_score(score.model_copy(update={"anomaly_id": "score-2"}))

    assert incident.incident_id == same_group.incident_id
    updated, change = service.transition(
        incident,
        IncidentStatus.INVESTIGATING,
        changed_at=datetime(2026, 9, 1, 10, 1, tzinfo=UTC),
        actor="operator-1",
        reason="reviewing evidence",
    )
    assert updated.status is IncidentStatus.INVESTIGATING
    assert change.from_status is IncidentStatus.OPEN

    try:
        service.transition(
            incident,
            IncidentStatus.RESOLVED,
            changed_at=datetime(2026, 9, 1, 10, 2, tzinfo=UTC),
            actor="operator-1",
        )
    except ValueError as error:
        assert "Invalid incident transition" in str(error)
    else:
        raise AssertionError("open incidents must not skip investigation")


def test_evidence_package_is_deterministic_and_warns_on_quality() -> None:
    score = AnomalyScore(
        anomaly_id="score-1", detector_name="ewma", detector_version="ewma-v1",
        entity_type="chain", entity_id="8453", chain_id=8453,
        detected_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC), score=0.9,
        severity=HealthStatus.CRITICAL, drivers=["rpc_latency"], feature_ids=["feature-1"],
    )
    incident = IncidentService().open_from_score(score)
    feature = FeatureSnapshot(
        feature_id="feature-1", feature_name="rpc_latency", feature_version="rpc-v1",
        entity_type="chain", entity_id="8453", chain_id=8453,
        measured_at=score.detected_at, window_minutes=15, value=2000,
        source_observation_ids=["observation-1"], quality_status="stale",
    )
    builder = EvidencePackageBuilder()
    package = builder.build(incident, score, [feature], generated_at=score.detected_at)
    repeat = builder.build(incident, score, [feature], generated_at=score.detected_at)
    assert package.package_id == repeat.package_id
    assert len(package.evidence) == 2
    assert package.quality_warnings == ["Feature feature-1 is stale."]
    assert package.unknowns
