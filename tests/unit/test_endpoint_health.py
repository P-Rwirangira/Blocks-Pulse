from datetime import UTC, datetime, timedelta

from blockpulse.chain_health.application.endpoint_health import calculate_endpoint_health
from blockpulse.domain import HealthStatus, RpcObservation


def test_endpoint_health_scores_failures_and_latency() -> None:
    base = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)
    observations = [
        RpcObservation(endpoint_name="base-a", chain_id=8453, observed_at=base, latency_ms=100, success=True),
        RpcObservation(endpoint_name="base-a", chain_id=8453, observed_at=base + timedelta(minutes=1), latency_ms=100, success=False),
        RpcObservation(endpoint_name="base-b", chain_id=8453, observed_at=base, latency_ms=2000, success=True),
    ]

    scores = calculate_endpoint_health(observations)

    assert [score.endpoint_name for score in scores] == ["base-a", "base-b"]
    assert scores[0].status is HealthStatus.WARNING
    assert scores[0].consecutive_failures == 1
    assert scores[1].status is HealthStatus.WARNING
