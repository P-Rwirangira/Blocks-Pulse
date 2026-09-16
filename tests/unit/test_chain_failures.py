import asyncio
from datetime import UTC, datetime

from blockpulse.collection_service import MultiChainCollectionService
from blockpulse.chain_registry import ChainDefinition
from blockpulse.domain import RpcObservation


class FailingProvider:
    name = "ethereum-a"
    chain_id = 1

    async def observe_latest_block(self, observed_at: datetime) -> RpcObservation:
        return RpcObservation(
            endpoint_name=self.name,
            chain_id=self.chain_id,
            observed_at=observed_at,
            latency_ms=500,
            success=False,
            error_type="timeout",
        )


class HealthyProvider:
    name = "base-a"
    chain_id = 8453

    async def observe_latest_block(self, observed_at: datetime) -> RpcObservation:
        return RpcObservation(
            endpoint_name=self.name,
            chain_id=self.chain_id,
            observed_at=observed_at,
            latency_ms=100,
            success=True,
            latest_block_number=100,
        )


class Repository:
    async def add_many(self, observations: list[RpcObservation]) -> int:
        self.observations = observations
        return len(observations)


def test_one_chain_failure_does_not_stop_other_chain() -> None:
    async def scenario() -> None:
        repository = Repository()
        services = {
            ChainDefinition("ethereum", 1, ("https://eth.example",)): [FailingProvider()],
            ChainDefinition("base", 8453, ("https://base.example",)): [HealthyProvider()],
        }
        result, _ = await MultiChainCollectionService(services, repository).collect_once(
            datetime.now(UTC)
        )
        assert result[1][0].success is False
        assert result[8453][0].success is True

    asyncio.run(scenario())

