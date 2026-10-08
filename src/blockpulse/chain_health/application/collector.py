"""Collection orchestration with retry and endpoint failover."""

import asyncio
from collections.abc import Sequence
from datetime import datetime

from blockpulse.domain.models import RpcObservation
from blockpulse.shared.ports import RpcProvider
from blockpulse.chain_health.application.circuit_breaker import EndpointCircuitBreaker


class RpcCollector:
    """Collect latest-block observations from configured providers."""

    def __init__(
        self,
        providers: Sequence[RpcProvider],
        retries: int = 1,
        retry_backoff_seconds: float = 0.5,
        failure_threshold: int = 3,
        circuit_cooldown_seconds: float = 30.0,
    ) -> None:
        if not providers:
            raise ValueError("at least one RPC provider is required")
        if retries < 0:
            raise ValueError("retries cannot be negative")
        if retry_backoff_seconds < 0:
            raise ValueError("retry backoff cannot be negative")
        self.providers = list(providers)
        self.retries = retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.breakers = {
            provider.name: EndpointCircuitBreaker(failure_threshold, circuit_cooldown_seconds)
            for provider in self.providers
        }

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
        breaker = self.breakers[provider.name]
        if not breaker.allow_request():
            return [
                RpcObservation(
                    endpoint_name=provider.name,
                    chain_id=provider.chain_id,
                    observed_at=observed_at,
                    latency_ms=0,
                    success=False,
                    error_type="circuit_open",
                )
            ]
        for attempt in range(self.retries + 1):
            observation = await provider.observe_latest_block(observed_at)
            observation = observation.model_copy(update={"attempt": attempt})
            attempts.append(observation)
            if observation.success:
                breaker.record_success()
                break
            breaker.record_failure()
            if attempt < self.retries and self.retry_backoff_seconds:
                await asyncio.sleep(self.retry_backoff_seconds * (2**attempt))
        return attempts
