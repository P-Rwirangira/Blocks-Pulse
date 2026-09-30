"""Explainable deterministic anomaly detector for RPC health."""

from blockpulse.domain import AnomalyEvent, HealthMetric, HealthStatus


def detect_rpc_anomaly(
    metric: HealthMetric,
    baseline_latency_ms: float,
    baseline_error_rate: float,
    baseline_block_disagreement: int = 0,
) -> AnomalyEvent | None:
    """Return an anomaly when current metrics breach a reproducible baseline."""

    drivers: list[str] = []
    ratios: list[float] = []
    if baseline_latency_ms > 0 and metric.p95_latency_ms > baseline_latency_ms:
        ratios.append(metric.p95_latency_ms / baseline_latency_ms)
        drivers.append("rpc_latency")
    if metric.error_rate > baseline_error_rate:
        denominator = max(baseline_error_rate, 0.01)
        ratios.append(metric.error_rate / denominator)
        drivers.append("rpc_errors")
    if metric.block_disagreement > baseline_block_disagreement:
        ratios.append(float(metric.block_disagreement - baseline_block_disagreement + 1))
        drivers.append("endpoint_disagreement")

    if not drivers:
        return None

    raw_score = min(1.0, max(ratios) / 10)
    score = max(0.1, raw_score)
    severity = metric.status
    if severity is HealthStatus.HEALTHY:
        severity = HealthStatus.WARNING
    event_id = f"rpc-health-{metric.chain_id}-{metric.measured_at.isoformat()}"
    return AnomalyEvent(
        event_id=event_id,
        chain_id=metric.chain_id,
        detected_at=metric.measured_at,
        score=score,
        status=severity,
        drivers=drivers,
        metric=metric,
    )

