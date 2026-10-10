"""Historical health projections from stored observations."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from blockpulse.chain_health.application.metrics import calculate_rpc_health
from blockpulse.domain.models import HealthMetric, RpcObservation


class HistoricalHealthProjection:
    """Build deterministic time buckets from already captured observations."""

    def build(
        self, observations: Sequence[RpcObservation], window_minutes: int
    ) -> list[HealthMetric]:
        """Calculate one health metric per UTC time bucket and chain."""

        if window_minutes <= 0:
            raise ValueError("window must be positive")
        buckets: dict[tuple[int, datetime], list[RpcObservation]] = defaultdict(list)
        window = timedelta(minutes=window_minutes)
        epoch = datetime.min.replace(tzinfo=UTC)
        for observation in observations:
            measured_at = observation.observed_at.astimezone(UTC)
            bucket_start = measured_at - (measured_at - epoch) % window
            buckets[(observation.chain_id, bucket_start)].append(observation)

        return [
            calculate_rpc_health(values, window_minutes)
            for _, values in sorted(buckets.items(), key=lambda item: item[0])
        ]
