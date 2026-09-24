from datetime import UTC, datetime

from blockpulse.domain import PoolDefinition
from blockpulse.rpc import RawLog
from blockpulse.v3_events import (
    V3_MINT_TOPIC,
    V3_SWAP_TOPIC,
    decode_v3_log,
)


POOL = PoolDefinition(
    pool_id="base-v3-weth-usdc",
    chain_id=8453,
    address="0xpool",
    version="v3",
    token0_symbol="WETH",
    token1_symbol="USDC",
    token0_decimals=18,
    token1_decimals=6,
    fee_tier=500,
    tick_spacing=10,
)


def word(value: int) -> str:
    return f"{value % (1 << 256):064x}"


def make_log(topic: str, data: str, topics: list[str] | None = None) -> RawLog:
    return RawLog(
        address="0xpool",
        topics=[topic, *(topics or [])],
        data="0x" + data,
        block_number=100,
        block_hash="0xblock",
        transaction_hash="0xtx",
        log_index=2,
    )


def test_decode_v3_swap_preserves_price_tick_and_liquidity() -> None:
    event = decode_v3_log(
        make_log(V3_SWAP_TOPIC, word(-10**18) + word(2_000_000) + word(2**96) + word(500_000) + word(-10), []),
        POOL,
        datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert event.event_type == "swap"
    assert event.amount0 == -10**18
    assert event.amount1 == 2_000_000
    assert event.sqrt_price_x96 == 2**96
    assert event.active_liquidity == 500_000
    assert event.tick == -10


def test_decode_v3_mint_reads_signed_tick_range() -> None:
    event = decode_v3_log(
        make_log(
            V3_MINT_TOPIC,
            word(1000) + word(10**18) + word(2_000_000),
            [word(0), word(-120), word(120)],
        ),
        POOL,
        datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert event.event_type == "mint"
    assert event.tick_lower == -120
    assert event.tick_upper == 120
    assert event.active_liquidity == 1000

