"""Application service for calculating current chain health."""

from blockpulse.domain import HealthMetric, RpcObservation
from blockpulse.monitoring import calculate_rpc_health
from blockpulse.storage import ObservationRepository


class HealthService:
    """Coordinate repository reads and pure monitoring calculations."""

    def __init__(self, repository: ObservationRepository) -> None:
        self.repository = repository

    async def current(self, chain_id: int, window_minutes: int) -> HealthMetric:
        rows = await self.repository.recent(chain_id)
        if not rows:
            raise LookupError(f"no observations found for chain {chain_id}")
        observations = [
            RpcObservation(
                endpoint_name=row.endpoint_name,
                chain_id=row.chain_id,
                observed_at=row.observed_at,
                latency_ms=row.latency_ms,
                success=row.success,
                latest_block_number=row.latest_block_number,
                error_type=row.error_type,
            )
            for row in rows
        ]
        return calculate_rpc_health(observations, window_minutes)

