"""Structured counters for collection-cycle operations."""

from dataclasses import dataclass
from typing import Protocol

from blockpulse.domain.models import RpcObservation


class MetricsSink(Protocol):
    """Application-facing metrics port implemented by infrastructure adapters."""

    def observe_rpc(self, chain_id: int, success: bool, latency_ms: float) -> None:
        """Record one RPC observation."""


@dataclass(slots=True)
class CollectionStats:
    """Process-local counters suitable for logs and health dashboards."""

    cycles: int = 0
    observations: int = 0
    successful_observations: int = 0
    failed_observations: int = 0
    inserted_observations: int = 0
    last_duration_ms: float = 0.0

    def record(self, observations: list[RpcObservation], inserted: int, duration_ms: float) -> None:
        """Record one completed collection cycle."""

        self.cycles += 1
        self.observations += len(observations)
        self.successful_observations += sum(item.success for item in observations)
        self.failed_observations += sum(not item.success for item in observations)
        self.inserted_observations += inserted
        self.last_duration_ms = duration_ms

    def snapshot(self) -> dict[str, int | float]:
        """Return stable flat fields for structured logging."""

        return {
            "collection_cycles": self.cycles,
            "collection_observations": self.observations,
            "collection_successes": self.successful_observations,
            "collection_failures": self.failed_observations,
            "collection_inserted": self.inserted_observations,
            "collection_last_duration_ms": round(self.last_duration_ms, 2),
        }
