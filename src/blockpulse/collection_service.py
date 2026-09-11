"""Application service for one Base observation collection cycle."""

from collections.abc import Sequence
from datetime import datetime

from blockpulse.collector import RpcCollector
from blockpulse.domain import RpcObservation
from blockpulse.ports import RpcProvider
from blockpulse.storage import ObservationRepository


class CollectionService:
    """Coordinate collection and durable persistence."""

    def __init__(self, providers: Sequence[RpcProvider], repository: ObservationRepository) -> None:
        self.collector = RpcCollector(providers)
        self.repository = repository

    async def collect_once(self, observed_at: datetime) -> tuple[list[RpcObservation], int]:
        """Collect all configured endpoints and persist the observations."""

        observations = await self.collector.collect_all(observed_at)
        inserted = await self.repository.add_many(observations)
        return observations, inserted

