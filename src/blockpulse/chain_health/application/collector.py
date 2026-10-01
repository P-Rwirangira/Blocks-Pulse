"""Collection orchestration with retry and endpoint failover."""

import asyncio
from collections.abc import Sequence
from datetime import datetime

from blockpulse.domain.models import RpcObservation
from blockpulse.shared.ports import RpcProvider


class RpcCollector:
    """Collect latest-block observations from configured providers."""

    def __init__(self, providers: Sequence[RpcProvider], retries: int = 1) -> None:
        if not providers:
            raise ValueError("at least one RPC provider is required")
        if retries < 0:
            raise ValueError("retries cannot be negative")
        self.providers = list(providers)
        self.retries = retries

    async def collect_all(self, observed_at: datetime) -> list[RpcObservation]:
        """Observe every endpoint so endpoint health can be compared."""

        results = await asyncio.gather(
            *(self._observe_with_retry(provider, observed_at) for provider in self.providers)
        )
        return [observation for attempts in results for observation in attempts]

    async def collect_with_failover(self, observed_at: datetime) -> list[RpcObservation]:
        """Try providers in order and stop after the first successful endpoint."""

        observations: list[RpcObservation] = []
        for provider in self.providers:
            attempts = await self._observe_with_retry(provider, observed_at)
            observations.extend(attempts)
            if attempts[-1].success:
                break
        return observations

    async def _observe_with_retry(
        self, provider: RpcProvider, observed_at: datetime
    ) -> list[RpcObservation]:
        attempts: list[RpcObservation] = []
        for _ in range(self.retries + 1):
            observation = await provider.observe_latest_block(observed_at)
            attempts.append(observation)
            if observation.success:
                break
        return attempts
