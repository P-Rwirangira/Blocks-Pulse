"""Application service for materializing historical chain-health metrics."""

from blockpulse.chain_health.application.backfill import HistoricalHealthProjection
from blockpulse.domain.models import RpcObservation
from blockpulse.infrastructure.database.repositories import HealthMetricRepository, ObservationRepository


class HistoricalHealthBackfillService:
    """Read stored observations and persist idempotent metric projections."""

    def __init__(
        self,
        observations: ObservationRepository,
        metrics: HealthMetricRepository,
    ) -> None:
        self.observations = observations
        self.metrics = metrics

    async def backfill_chain(
        self, chain_id: int, window_minutes: int, limit: int = 10_000
    ) -> tuple[int, int]:
        """Return `(metrics_built, metrics_inserted)` for one chain."""

        rows = await self.observations.recent(chain_id, limit=limit)
        values = [
            RpcObservation(
                endpoint_name=row.endpoint_name,
                chain_id=row.chain_id,
                observed_at=row.observed_at,
                attempt=row.attempt,
                latency_ms=row.latency_ms,
                success=row.success,
                latest_block_number=row.latest_block_number,
                latest_block_hash=row.latest_block_hash,
                latest_parent_hash=row.latest_parent_hash,
                error_type=row.error_type,
                raw_payload=row.raw_payload,
            )
            for row in rows
        ]
        metrics_built = HistoricalHealthProjection().build(values, window_minutes)
        inserted = await self.metrics.add_many(metrics_built)
        return len(metrics_built), inserted
