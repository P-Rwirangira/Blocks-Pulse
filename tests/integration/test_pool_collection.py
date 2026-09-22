import asyncio
from datetime import UTC, datetime

from blockpulse.domain import PoolDefinition
from blockpulse.pool_collection import PoolCollectionService
from blockpulse.pool_events import V2_SYNC_TOPIC
from blockpulse.rpc import RawLog
from blockpulse.storage import Database, PoolCursorRepository, PoolEventRepository


POOL = PoolDefinition(
    pool_id="base-weth-usdc",
    chain_id=8453,
    address="0xpool",
    token0_symbol="WETH",
    token1_symbol="USDC",
    token0_decimals=18,
    token1_decimals=6,
    start_block=100,
)


class FakeProvider:
    name = "base-a"
    chain_id = 8453

    async def observe_latest_block(self, observed_at: datetime):
        from blockpulse.domain import RpcObservation

        return RpcObservation(
            endpoint_name=self.name,
            chain_id=self.chain_id,
            observed_at=observed_at,
            latency_ms=10,
            success=True,
            latest_block_number=105,
        )

    async def get_logs(self, address: str, from_block: int, to_block: int, topics: list[str]):
        assert (address, from_block, to_block) == ("0xpool", 100, 103)
        return [
            RawLog(
                address="0xpool",
                topics=[V2_SYNC_TOPIC],
                data="0x" + f"{2 * 10**18:064x}" + f"{3_000_000:064x}",
                block_number=101,
                block_hash="0xblock",
                transaction_hash="0xtx",
                log_index=0,
            )
        ]


def test_pool_collection_uses_confirmed_cursor_range() -> None:
    async def scenario() -> None:
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_schema()
        async with database.sessions() as session:
            service = PoolCollectionService(
                FakeProvider(),
                PoolEventRepository(session),
                PoolCursorRepository(session),
                confirmations=2,
            )
            events, inserted = await service.collect_once(POOL, datetime.now(UTC))
            assert len(events) == 1
            assert inserted == 1
            assert await PoolCursorRepository(session).get(POOL.pool_id) == 103
        await database.close()

    asyncio.run(scenario())

