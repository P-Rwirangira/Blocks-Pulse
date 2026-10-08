import asyncio
from datetime import UTC, datetime

import pytest

from blockpulse.collector import RpcCollector
from blockpulse.domain import RpcObservation


class FakeProvider:
    def __init__(self, name: str, outcomes: list[bool]) -> None:
        self.name = name
        self.chain_id = 8453
        self.outcomes = outcomes
        self.calls = 0

    async def observe_latest_block(self, observed_at: datetime) -> RpcObservation:
        success = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        return RpcObservation(
            endpoint_name=self.name,
            chain_id=self.chain_id,
            observed_at=observed_at,
            latency_ms=10,
            success=success,
            latest_block_number=100 if success else None,
            error_type=None if success else "timeout",
        )


def test_collector_retries_then_succeeds() -> None:
    async def scenario() -> None:
        provider = FakeProvider("base-a", [False, True])
        observations = await RpcCollector([provider], retries=1).collect_all(
            datetime.now(UTC)
        )
        assert [item.success for item in observations] == [False, True]

    asyncio.run(scenario())


def test_collector_fails_over_to_second_provider() -> None:
    async def scenario() -> None:
        first = FakeProvider("base-a", [False])
        second = FakeProvider("base-b", [True])
        observations = await RpcCollector([first, second], retries=0).collect_with_failover(
            datetime.now(UTC)
        )
        assert [item.endpoint_name for item in observations] == ["base-a", "base-b"]
        assert observations[-1].success is True

    asyncio.run(scenario())


def test_collector_uses_exponential_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        delays: list[float] = []

        async def fake_sleep(delay: float) -> None:
            delays.append(delay)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        provider = FakeProvider("base-a", [False, False, True])
        observations = await RpcCollector(
            [provider], retries=2, retry_backoff_seconds=0.25
        ).collect_all(datetime.now(UTC))

        assert [item.success for item in observations] == [False, False, True]
        assert [item.attempt for item in observations] == [0, 1, 2]
        assert delays == [0.25, 0.5]

    asyncio.run(scenario())


def test_collector_rejects_negative_backoff() -> None:
    with pytest.raises(ValueError, match="backoff"):
        RpcCollector([FakeProvider("base-a", [True])], retry_backoff_seconds=-1)


def test_collector_opens_circuit_after_repeated_failures() -> None:
    async def scenario() -> None:
        provider = FakeProvider("base-a", [False, False, False, True])
        collector = RpcCollector([provider], retries=0, failure_threshold=2)
        observed_at = datetime.now(UTC)

        first = await collector.collect_all(observed_at)
        second = await collector.collect_all(observed_at)
        third = await collector.collect_all(observed_at)

        assert first[0].error_type == "timeout"
        assert second[0].error_type == "timeout"
        assert third[0].error_type == "circuit_open"
        assert provider.calls == 2

    asyncio.run(scenario())
