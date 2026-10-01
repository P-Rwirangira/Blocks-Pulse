"""Ports that isolate domain services from external infrastructure."""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from blockpulse.domain.models import RpcObservation
from blockpulse.infrastructure.rpc.jsonrpc import RawLog


class RpcProvider(Protocol):
    """Port for reading the latest block from an RPC endpoint."""

    name: str
    chain_id: int

    async def observe_latest_block(self, observed_at: datetime) -> RpcObservation:
        """Read and measure the latest block."""

    async def get_logs(
        self, address: str, from_block: int, to_block: int, topics: list[str]
    ) -> list[RawLog]:
        """Read logs for one address and block range."""

    async def eth_call(self, to: str, data: str, block_tag: str = "latest") -> str:
        """Execute a read-only contract call."""


class ObservationRepository(Protocol):
    """Port for durable observation storage."""

    async def add_many(self, observations: Sequence[RpcObservation]) -> int:
        """Persist observations idempotently and return new row count."""
