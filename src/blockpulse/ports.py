"""Ports that isolate domain services from external infrastructure."""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from blockpulse.domain import RpcObservation


class RpcProvider(Protocol):
    """Port for reading the latest block from an RPC endpoint."""

    name: str
    chain_id: int

    async def observe_latest_block(self, observed_at: datetime) -> RpcObservation:
        """Read and measure the latest block."""


class ObservationRepository(Protocol):
    """Port for durable observation storage."""

    async def add_many(self, observations: Sequence[RpcObservation]) -> int:
        """Persist observations idempotently and return new row count."""

