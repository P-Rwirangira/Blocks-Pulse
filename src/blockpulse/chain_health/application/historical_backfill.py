"""Bounded, sampled historical block ingestion for chain-health features."""

import asyncio
from datetime import UTC, date, datetime, time, timedelta

from blockpulse.domain.models import HistoricalBlock
from blockpulse.infrastructure.database.repositories import (
    HistoricalBackfillCursorRepository,
    HistoricalBlockRepository,
)
from blockpulse.infrastructure.rpc.jsonrpc import JsonRpcProvider


BLOCK_TIME_SECONDS = {1: 12.0, 8453: 2.0, 42161: 0.25}
HISTORICAL_FETCH_BATCH_SIZE = 8


class HistoricalBlockBackfillService:
    """Sample block headers over a date range without fabricating RPC telemetry."""

    def __init__(
        self,
        provider: JsonRpcProvider,
        blocks: HistoricalBlockRepository,
        cursors: HistoricalBackfillCursorRepository,
    ) -> None:
        self.provider = provider
        self.blocks = blocks
        self.cursors = cursors

    async def backfill(
        self,
        start_date: date,
        end_date: date,
        sample_minutes: int = 60,
        max_samples: int = 5_000,
    ) -> tuple[int, int]:
        """Return `(fetched, inserted)` for an inclusive UTC date range."""

        if end_date < start_date:
            raise ValueError("end date must not precede start date")
        if sample_minutes <= 0:
            raise ValueError("sample interval must be positive")
        if max_samples <= 0:
            raise ValueError("max samples must be positive")

        start = datetime.combine(start_date, time.min, tzinfo=UTC)
        end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
        latest = await self._block("latest")
        latest_time = self._block_time(latest)
        if latest_time < start:
            raise ValueError("requested range is newer than the RPC node head")

        start_block = await self._find_block_at_or_after(start, 0, int(latest["number"], 16))
        end_block = await self._find_block_at_or_after(end, start_block, int(latest["number"], 16))
        end_block = min(end_block, int(latest["number"], 16))
        step = max(1, round(sample_minutes * 60 / BLOCK_TIME_SECONDS.get(self.provider.chain_id, 12.0)))
        key = f"{self.provider.chain_id}:{start_date.isoformat()}:{end_date.isoformat()}:{sample_minutes}"
        cursor = await self.cursors.get(key)
        next_block = max(start_block, (cursor.last_block_number + step) if cursor else start_block)

        fetched = inserted = 0
        while next_block <= end_block and fetched < max_samples:
            batch_numbers = list(
                range(
                    next_block,
                    min(end_block + 1, next_block + HISTORICAL_FETCH_BATCH_SIZE * step),
                    step,
                )
            )
            payloads = await asyncio.gather(*(self._block(hex(number)) for number in batch_numbers))
            for block_number, payload in zip(batch_numbers, payloads, strict=True):
                block_time = self._block_time(payload)
                if block_time >= end:
                    return fetched, inserted
                if block_time >= start:
                    historical = self._to_model(payload, block_time)
                    fetched += 1
                    inserted += int(await self.blocks.add(historical))
                    await self.cursors.save(
                        key,
                        self.provider.chain_id,
                        start,
                        end,
                        sample_minutes,
                        block_number,
                    )
                if fetched >= max_samples:
                    return fetched, inserted
            next_block = batch_numbers[-1] + step
        return fetched, inserted

    async def _block(self, tag: str) -> dict:
        return await self.provider.get_block_by_number(tag)

    async def _find_block_at_or_after(self, target: datetime, low: int, high: int) -> int:
        while low < high:
            middle = (low + high) // 2
            payload = await self._block(hex(middle))
            if self._block_time(payload) < target:
                low = middle + 1
            else:
                high = middle
        return low

    def _to_model(self, payload: dict, block_time: datetime) -> HistoricalBlock:
        number = int(payload["number"], 16)
        block_hash = payload.get("hash")
        if not isinstance(block_hash, str):
            raise ValueError("historical block has no canonical hash")
        return HistoricalBlock(
            chain_id=self.provider.chain_id,
            block_number=number,
            block_hash=block_hash,
            parent_hash=payload.get("parentHash"),
            block_timestamp=block_time,
            transaction_count=len(payload.get("transactions", [])),
            gas_used=self._optional_int(payload.get("gasUsed")),
            gas_limit=self._optional_int(payload.get("gasLimit")),
            base_fee_per_gas=self._optional_int(payload.get("baseFeePerGas")),
            collected_at=datetime.now(UTC),
            raw_payload=payload,
        )

    @staticmethod
    def _block_time(payload: dict) -> datetime:
        return datetime.fromtimestamp(int(payload["timestamp"], 16), tz=UTC)

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return int(value, 16) if isinstance(value, str) else None
