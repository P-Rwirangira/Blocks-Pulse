import asyncio
from datetime import UTC, datetime

from blockpulse.collection_service import CollectionService
from blockpulse.collection_service import MultiChainCollectionService
from blockpulse.chain_registry import ChainDefinition
from blockpulse.domain import RpcObservation


class FakeProvider:
    name = "base-a"
    chain_id = 8453

    async def observe_latest_block(self, observed_at: datetime) -> RpcObservation:
        return RpcObservation(
            endpoint_name=self.name,
            chain_id=self.chain_id,
            observed_at=observed_at,
            latency_ms=5,
            success=True,
            latest_block_number=123,
        )


class FakeRepository:
    def __init__(self) -> None:
        self.saved: list[RpcObservation] = []

    async def add_many(self, observations: list[RpcObservation]) -> int:
        self.saved.extend(observations)
        return len(observations)


def test_collection_service_persists_one_cycle() -> None:
    repository = FakeRepository()
    service = CollectionService([FakeProvider()], repository)
    observations, inserted = asyncio.run(service.collect_once(datetime.now(UTC)))

    assert len(observations) == 1
    assert inserted == 1
    assert repository.saved[0].latest_block_number == 123


def test_multi_chain_service_collects_each_chain() -> None:
    async def scenario() -> None:
        repository = FakeRepository()
        chains = {
            ChainDefinition("base", 8453, ("https://base.example",)): [FakeProvider()],
            ChainDefinition("arbitrum", 42161, ("https://arb.example",)): [FakeProvider()],
        }
        results, inserted = await MultiChainCollectionService(chains, repository).collect_once(
            datetime.now(UTC)
        )
        assert set(results) == {8453, 42161}
        assert inserted == 2

    asyncio.run(scenario())
