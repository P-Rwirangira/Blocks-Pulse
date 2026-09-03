from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from blockpulse.domain import HealthMetric, HealthStatus, RpcObservation


def test_rpc_observation_requires_valid_chain_id() -> None:
    with pytest.raises(ValidationError):
        RpcObservation(
            endpoint_name="base-a",
            chain_id=0,
            observed_at=datetime.now(UTC),
            latency_ms=10,
            success=True,
        )


def test_health_metric_accepts_healthy_state() -> None:
    metric = HealthMetric(
        chain_id=8453,
        measured_at=datetime.now(UTC),
        window_minutes=15,
        request_count=10,
        error_rate=0,
        p95_latency_ms=100,
        status=HealthStatus.HEALTHY,
    )

    assert metric.status is HealthStatus.HEALTHY

