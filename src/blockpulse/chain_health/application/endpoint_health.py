"""Provider-level reliability scoring."""

from collections import defaultdict
from collections.abc import Sequence

from blockpulse.domain.models import EndpointHealthScore, HealthStatus, RpcObservation


def calculate_endpoint_health(
    observations: Sequence[RpcObservation],
) -> list[EndpointHealthScore]:
    """Score each endpoint using transparent availability and latency signals."""

    grouped: dict[str, list[RpcObservation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.endpoint_name].append(observation)

    scores: list[EndpointHealthScore] = []
    for endpoint_name, values in sorted(grouped.items()):
        successful = [item for item in values if item.success]
        success_rate = len(successful) / len(values)
        average_latency = sum(item.latency_ms for item in values) / len(values)
        consecutive_failures = 0
        for item in sorted(values, key=lambda value: (value.observed_at, value.attempt), reverse=True):
            if item.success:
                break
            consecutive_failures += 1
        latency_factor = min(1.0, 1000 / max(average_latency, 1))
        score = round(success_rate * latency_factor, 4)
        status = HealthStatus.HEALTHY
        if score < 0.5 or consecutive_failures >= 3:
            status = HealthStatus.CRITICAL
        elif score < 0.9 or consecutive_failures:
            status = HealthStatus.WARNING
        scores.append(
            EndpointHealthScore(
                endpoint_name=endpoint_name,
                chain_id=values[0].chain_id,
                request_count=len(values),
                success_rate=success_rate,
                average_latency_ms=average_latency,
                consecutive_failures=consecutive_failures,
                score=score,
                status=status,
            )
        )
    return scores
