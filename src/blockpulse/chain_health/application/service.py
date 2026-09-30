"""Application service for calculating current chain health."""

from datetime import UTC, datetime

from blockpulse.chain_registry import ChainDefinition
from blockpulse.domain import ChainHealthSummary, HealthMetric, HealthOverview, RpcObservation
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

    async def overview(
        self, chains: tuple[ChainDefinition, ...], window_minutes: int
    ) -> HealthOverview:
        """Build a cross-chain view, omitting chains without observations."""

        summaries: list[ChainHealthSummary] = []
        for chain in chains:
            try:
                metric = await self.current(chain.chain_id, window_minutes)
            except LookupError:
                continue
            summaries.append(ChainHealthSummary(name=chain.name, metric=metric))

        rank = {"healthy": 1, "warning": 2, "critical": 3}
        summaries.sort(key=lambda item: rank[item.metric.status.value])
        measured_at = max(
            (summary.metric.measured_at for summary in summaries),
            default=datetime.now(UTC),
        )
        return HealthOverview(
            measured_at=measured_at,
            chains=summaries,
            healthiest_chain=summaries[0].name if summaries else None,
            least_healthy_chain=summaries[-1].name if summaries else None,
        )
