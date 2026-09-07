from datetime import UTC, datetime

from blockpulse.domain import HealthStatus, RpcObservation
from blockpulse.monitoring import calculate_rpc_health, percentile


def observation(
    endpoint: str, latency: float, block: int | None, success: bool = True
) -> RpcObservation:
    return RpcObservation(
        endpoint_name=endpoint,
        chain_id=8453,
        observed_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        latency_ms=latency,
        success=success,
        latest_block_number=block,
        error_type=None if success else "timeout",
    )


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([10, 20, 30, 40], 0.95) == 40


def test_health_metric_detects_warning_conditions() -> None:
    metric = calculate_rpc_health(
        [observation("base-a", 120, 100), observation("base-b", 1_200, 98)],
        window_minutes=15,
    )

    assert metric.p95_latency_ms == 1_200
    assert metric.block_disagreement == 2
    assert metric.status is HealthStatus.WARNING


def test_health_metric_detects_critical_error_rate() -> None:
    values = [observation("base-a", 100, 100) for _ in range(6)]
    values.extend(
        observation("base-a", 100, None, success=False)
        for _ in range(4)
    )

    metric = calculate_rpc_health(values, window_minutes=15)
    assert metric.error_rate == 0.4
    assert metric.status is HealthStatus.CRITICAL
