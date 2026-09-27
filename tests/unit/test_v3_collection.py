import asyncio
from datetime import UTC, datetime

from blockpulse.domain import PoolDefinition, RpcObservation
from blockpulse.pool_collection import PoolCollectionService
from blockpulse.v3_events import V3_SWAP_TOPIC


POOL = PoolDefinition(
    pool_id="base-v3-weth-usdc",
    chain_id=8453,
    address="0xpool",
    version="v3",
    token0_symbol="WETH",
    token1_symbol="USDC",
    token0_decimals=18,
    token1_decimals=6,
    start_block=100,
)


def word(value: int) -> str:
    return f"{value % (1 << 256):064x}"


class FakeProvider:
    async def observe_latest_block(self, observed_at: datetime) -> RpcObservation:
        return RpcObservation(
            endpoint_name="base-a",
            chain_id=8453,
            observed_at=observed_at,
            latency_ms=10,
            success=True,
            latest_block_number=105,
        )

    async def get_logs(self, address: str, from_block: int, to_block: int, topics: list[str]):
        from blockpulse.rpc import RawLog

        assert V3_SWAP_TOPIC in topics
        return [
            RawLog(
                address=address,
                topics=[V3_SWAP_TOPIC],
                data="0x" + word(-10**18) + word(2_000_000) + word(2**96) + word(500_000) + word(-10),
                block_number=101,
                block_hash="0xblock",
                transaction_hash="0xtx",
                log_index=0,
            )
        ]


class Repository:
    async def add_many(self, events):
        self.events = events
        return len(events)


class Cursor:
    async def get(self, pool_id: str) -> int:
        return -1

    async def advance(self, pool_id: str, block: int) -> None:
        self.block = block


def test_pool_collection_selects_v3_adapter() -> None:
    async def scenario() -> None:
        repository = Repository()
        service = PoolCollectionService(FakeProvider(), repository, Cursor(), confirmations=2)
        events, inserted = await service.collect_once(POOL, datetime.now(UTC))
        assert events[0].event_type == "swap"
        assert inserted == 1

    asyncio.run(scenario())
