from datetime import UTC, datetime

from blockpulse.domain import PoolDefinition
from blockpulse.pool_events import V2_SWAP_TOPIC, V2_SYNC_TOPIC, decode_v2_log
from blockpulse.rpc import RawLog


POOL = PoolDefinition(
    pool_id="base-weth-usdc",
    chain_id=8453,
    address="0xpool",
    token0_symbol="WETH",
    token1_symbol="USDC",
    token0_decimals=18,
    token1_decimals=6,
)


def word(value: int) -> str:
    return f"{value:064x}"


def make_log(topic: str, data: str) -> RawLog:
    return RawLog(
        address="0xpool",
        topics=[topic],
        data="0x" + data,
        block_number=100,
        block_hash="0xblock",
        transaction_hash="0xtx",
        log_index=2,
    )


def test_decode_v2_sync_normalizes_decimals() -> None:
    event = decode_v2_log(
        make_log(V2_SYNC_TOPIC, word(2 * 10**18) + word(3_000_000)),
        POOL,
        datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert event.event_type == "sync"
    assert event.reserve0 == 2
    assert event.reserve1 == 3


def test_decode_v2_swap_normalizes_net_amounts() -> None:
    event = decode_v2_log(
        make_log(V2_SWAP_TOPIC, word(10**18) + word(0) + word(0) + word(2_000_000)),
        POOL,
        datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert event.event_type == "swap"
    assert event.amount0 == 1
    assert event.amount1 == -2
    assert event.event_id == "8453:0xtx:2"

