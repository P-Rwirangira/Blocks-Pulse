from datetime import UTC, datetime

from blockpulse.detectors import detect_rpc_anomaly
from blockpulse.domain import AnomalyScore, FeatureSnapshot, HealthMetric, HealthStatus, IncidentStatus, RpcObservation
from blockpulse.incidents import IncidentService
from blockpulse.incidents.application.ai_validation import AIResponseValidator
from blockpulse.incidents.application.ai_evaluation import AIValidationCase, AIValidationEvaluator
from blockpulse.incidents.application.evidence import EvidencePackageBuilder
from blockpulse.incidents.application.tools import ToolRequest, package_tool_registry
from blockpulse.infrastructure.observability import MetricsRegistry


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
    later = service.open_from_score(
        score.model_copy(update={"anomaly_id": "score-3", "detected_at": datetime(2026, 9, 1, 10, 16, tzinfo=UTC)})
    )
    assert later.incident_id != incident.incident_id
    try:
        service.open_from_score(score, dedupe_window_minutes=0)
    except ValueError as error:
        assert "positive" in str(error)
    else:
        raise AssertionError("invalid deduplication windows must be rejected")
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

    enriched = builder.build(
        incident,
        score,
        [],
        generated_at=score.detected_at,
        observations=[RpcObservation(
            endpoint_name="base-a", chain_id=8453, observed_at=score.detected_at,
            latency_ms=2000, success=False, error_type="timeout", latest_block_number=123,
        )],
        quality_warnings=["observation window is stale"],
    )
    assert {item.evidence_type for item in enriched.evidence} == {"anomaly_score", "rpc_observation"}
    assert "observation window is stale" in enriched.quality_warnings


def test_read_only_tools_are_allow_listed_and_evidence_bearing() -> None:
    score = AnomalyScore(
        anomaly_id="score-2", detector_name="mad", detector_version="mad-v1",
        entity_type="chain", entity_id="1", chain_id=1,
        detected_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC), score=0.7,
        severity=HealthStatus.WARNING, drivers=["rpc_error_rate"], feature_ids=["feature-2"],
    )
    package = EvidencePackageBuilder().build(
        IncidentService().open_from_score(score), score, [], generated_at=score.detected_at
    )
    registry = package_tool_registry(package)
    result = registry.execute(ToolRequest(tool_name="incident.summary"))
    assert result.evidence_ids
    with_error = ToolRequest(tool_name="incident.evidence", arguments={"evidence_id": "missing"})
    try:
        registry.execute(with_error)
    except ValueError as error:
        assert "not present" in str(error)
    else:
        raise AssertionError("unknown evidence must be rejected")


def test_ai_response_validator_requires_grounded_claims_and_quality_disclosure() -> None:
    score = AnomalyScore(
        anomaly_id="score-3", detector_name="mad", detector_version="mad-v1",
        entity_type="chain", entity_id="1", chain_id=1,
        detected_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC), score=0.7,
        severity=HealthStatus.WARNING, drivers=["rpc_error_rate"], feature_ids=["feature-3"],
    )
    incident = IncidentService().open_from_score(score)
    package = EvidencePackageBuilder().build(
        incident, score, [], generated_at=score.detected_at
    )
    from blockpulse.domain import AIClaim, AIInvestigationResponse

    anomaly_evidence = package.evidence[0]
    response = AIInvestigationResponse(
        incident_id=incident.incident_id,
        summary="The detector found an anomaly.",
        claims=[AIClaim(text="The score was 0.7.", evidence_ids=[anomaly_evidence.evidence_id], numeric_value=0.7)],
        confidence=0.8,
        unknowns=["Root cause is unknown."],
    )
    validated = AIResponseValidator().validate(response, package)
    assert validated.grounded is True

    invalid = response.model_copy(
        update={"claims": [response.claims[0].model_copy(update={"numeric_value": 0.8})]}
    )
    try:
        AIResponseValidator().validate(invalid, package)
    except ValueError as error:
        assert "numeric claim" in str(error)
    else:
        raise AssertionError("unsupported numerical claims must be rejected")


def test_ai_validation_evaluator_covers_unsafe_response_cases() -> None:
    score = AnomalyScore(
        anomaly_id="score-4", detector_name="mad", detector_version="mad-v1",
        entity_type="chain", entity_id="1", chain_id=1,
        detected_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC), score=0.7,
        severity=HealthStatus.WARNING, drivers=["rpc_error_rate"], feature_ids=["feature-4"],
    )
    incident = IncidentService().open_from_score(score)
    package = EvidencePackageBuilder().build(incident, score, [], generated_at=score.detected_at)
    from blockpulse.domain import AIClaim, AIInvestigationResponse

    evidence_id = package.evidence[0].evidence_id
    valid = AIInvestigationResponse(
        incident_id=incident.incident_id, summary="Observed anomaly.", confidence=0.8,
        unknowns=["Root cause unknown."],
        claims=[AIClaim(text="Score is 0.7", evidence_ids=[evidence_id], numeric_value=0.7)],
    )
    missing_citation = valid.model_copy(
        update={"claims": [AIClaim(text="Unsupported", evidence_ids=["missing"])]}
    )
    metrics = MetricsRegistry()
    result = AIValidationEvaluator(metrics=metrics).evaluate(package, [
        AIValidationCase(name="valid", response=valid, expected_valid=True),
        AIValidationCase(name="missing-citation", response=missing_citation, expected_valid=False),
    ])
    assert result.total == 2
    assert result.passed == 2
    assert result.failed_cases == []
    assert "blockpulse_ai_validation_total" in metrics.render().decode()
