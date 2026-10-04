"""Long-running orchestration for scheduled collection cycles."""

import asyncio
from collections.abc import Awaitable, Callable


class CollectionWorker:
    """Run a collection callback at a bounded, configurable interval."""

    def __init__(
        self,
        collect_once: Callable[[], Awaitable[int]],
        interval_seconds: float,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("collection interval must be positive")
        self.collect_once = collect_once
        self.interval_seconds = interval_seconds

    async def run(self, stop_event: asyncio.Event | None = None) -> None:
        """Collect until cancellation or an optional stop event is set."""

        stop_event = stop_event or asyncio.Event()
        while not stop_event.is_set():
            await self.collect_once()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                continue
