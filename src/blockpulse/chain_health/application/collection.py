"""Application service for one Base observation collection cycle."""

import asyncio
from collections.abc import Sequence
from datetime import datetime

from blockpulse.chain_health.application.collector import RpcCollector
from blockpulse.domain.models import RpcObservation
from blockpulse.infrastructure.config.chains import ChainDefinition
from blockpulse.infrastructure.database.repositories import ObservationRepository
from blockpulse.shared.ports import RpcProvider


class CollectionService:
    """Coordinate collection and durable persistence."""

    def __init__(
        self,
        providers: Sequence[RpcProvider],
        repository: ObservationRepository,
        retries: int = 1,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self.collector = RpcCollector(providers, retries, retry_backoff_seconds)
        self.repository = repository

    async def collect_once(self, observed_at: datetime) -> tuple[list[RpcObservation], int]:
        """Collect all configured endpoints and persist the observations."""

        observations = await self.collector.collect_all(observed_at)
        inserted = await self.repository.add_many(observations)
        return observations, inserted


class MultiChainCollectionService:
    """Coordinate independent collection cycles for several chains."""

    def __init__(
        self,
        providers_by_chain: dict[ChainDefinition, Sequence[RpcProvider]],
        repository: ObservationRepository,
        retries: int = 1,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self.collectors = {
            chain: RpcCollector(providers, retries, retry_backoff_seconds)
            for chain, providers in providers_by_chain.items()
        }
        self.repository = repository

    async def collect_once(
        self, observed_at: datetime
    ) -> tuple[dict[int, list[RpcObservation]], int]:
        """Collect all enabled chains and persist observations in one cycle."""

        results = await asyncio.gather(
            *(collector.collect_all(observed_at) for collector in self.collectors.values())
        )
        observations_by_chain = {
            chain.chain_id: observations
            for chain, observations in zip(self.collectors, results, strict=True)
        }
        observations = [item for values in observations_by_chain.values() for item in values]
        inserted = await self.repository.add_many(observations)
        return observations_by_chain, inserted
