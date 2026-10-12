import asyncio
from datetime import UTC, datetime

from blockpulse.chain_health.application.historical_service import HistoricalHealthBackfillService
from blockpulse.domain import HealthMetric, HealthStatus, RpcObservation


class FakeObservations:
    async def recent(self, chain_id: int, limit: int):
        return [
            RpcObservation(
                endpoint_name="base-a",
                chain_id=chain_id,
                observed_at=datetime(2026, 10, 12, 9, 0, tzinfo=UTC),
                latency_ms=100,
                success=True,
                latest_block_number=100,
            )
        ]


class FakeMetrics:
    async def add_many(self, metrics: list[HealthMetric]) -> int:
        assert len(metrics) == 1
        assert metrics[0].status is HealthStatus.HEALTHY
        return 1


def test_historical_service_materializes_metrics() -> None:
    async def scenario() -> None:
        built, inserted = await HistoricalHealthBackfillService(
            FakeObservations(), FakeMetrics()
        ).backfill_chain(8453, 15)
        assert (built, inserted) == (1, 1)

    asyncio.run(scenario())
