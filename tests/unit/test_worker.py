import asyncio

import pytest

from blockpulse.chain_health.application.worker import CollectionWorker


def test_worker_runs_until_stop_event() -> None:
    async def scenario() -> None:
        stop_event = asyncio.Event()
        calls = 0

        async def collect() -> int:
            nonlocal calls
            calls += 1
            stop_event.set()
            return 0

        await CollectionWorker(collect, interval_seconds=1).run(stop_event)
        assert calls == 1

    asyncio.run(scenario())


def test_worker_rejects_non_positive_interval() -> None:
    async def collect() -> int:
        return 0

    with pytest.raises(ValueError, match="interval"):
        CollectionWorker(collect, interval_seconds=0)
