"""Deterministic health metrics derived from RPC observations."""

import math
from collections.abc import Sequence

from blockpulse.domain import HealthMetric, HealthStatus, RpcObservation


def percentile(values: Sequence[float], percentile_rank: float) -> float:
    """Return a nearest-rank percentile for a non-empty sequence."""

    if not values:
        raise ValueError("at least one value is required")
    if not 0 < percentile_rank <= 1:
        raise ValueError("percentile rank must be in (0, 1]")
    ordered = sorted(values)
    index = max(0, math.ceil(percentile_rank * len(ordered)) - 1)
    return ordered[index]


def calculate_rpc_health(
    observations: Sequence[RpcObservation], window_minutes: int
) -> HealthMetric:
    """Aggregate endpoint observations into one chain health metric."""

    if not observations:
        raise ValueError("cannot calculate health without observations")
    chain_ids = {observation.chain_id for observation in observations}
    if len(chain_ids) != 1:
        raise ValueError("all observations must belong to one chain")

    successful = [item for item in observations if item.success]
    latencies = [item.latency_ms for item in observations]
    block_numbers = [
        item.latest_block_number for item in successful if item.latest_block_number is not None
    ]
    error_rate = (len(observations) - len(successful)) / len(observations)
    block_disagreement = max(block_numbers) - min(block_numbers) if block_numbers else 0
    p95_latency = percentile(latencies, 0.95)
    status = health_status(error_rate, p95_latency, block_disagreement)

    return HealthMetric(
        chain_id=observations[0].chain_id,
        measured_at=max(item.observed_at for item in observations),
        window_minutes=window_minutes,
        request_count=len(observations),
        error_rate=error_rate,
        p95_latency_ms=p95_latency,
        latest_block_number=max(block_numbers) if block_numbers else None,
        block_disagreement=block_disagreement,
        status=status,
    )


def health_status(error_rate: float, p95_latency_ms: float, block_disagreement: int) -> HealthStatus:
    """Apply transparent MVP thresholds to a health metric."""

    if error_rate >= 0.30 or p95_latency_ms >= 5_000 or block_disagreement >= 10:
        return HealthStatus.CRITICAL
    if error_rate >= 0.10 or p95_latency_ms >= 1_000 or block_disagreement >= 2:
        return HealthStatus.WARNING
    return HealthStatus.HEALTHY

