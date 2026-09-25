import asyncio
from datetime import UTC, datetime

from blockpulse.domain import PoolDefinition
from blockpulse.v3_state import (
    LIQUIDITY_SELECTOR,
    SLOT0_SELECTOR,
    price_token1_per_token0,
    read_v3_state,
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
)


def word(value: int) -> str:
    return f"{value % (1 << 256):064x}"


class FakeProvider:
    async def eth_call(self, to: str, data: str, block_tag: str = "latest") -> str:
        assert to == "0xpool"
        if data == SLOT0_SELECTOR:
            return "0x" + word(2**96) + word(-12) + word(0) * 5
        assert data == LIQUIDITY_SELECTOR
        return "0x" + word(500_000)


def test_read_v3_state_decodes_slot0_and_liquidity() -> None:
    snapshot = asyncio.run(read_v3_state(FakeProvider(), POOL, datetime.now(UTC)))

    assert snapshot.sqrt_price_x96 == 2**96
    assert snapshot.tick == -12
    assert snapshot.active_liquidity == 500_000


def test_v3_price_conversion_applies_decimals() -> None:
    assert price_token1_per_token0(2**96, 18, 6) == 10**12

