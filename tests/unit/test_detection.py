from datetime import UTC, datetime

from blockpulse.detectors import detect_rpc_anomaly
from blockpulse.domain import HealthMetric, HealthStatus, IncidentStatus
from blockpulse.incidents import IncidentService


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

