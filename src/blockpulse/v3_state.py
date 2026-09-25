"""Read current Uniswap V3 state from the canonical pool view methods."""

from datetime import datetime

from eth_utils import keccak

from blockpulse.domain import PoolDefinition, V3StateSnapshot


def selector(signature: str) -> str:
    return "0x" + keccak(text=signature)[:4].hex()


SLOT0_SELECTOR = selector("slot0()")
LIQUIDITY_SELECTOR = selector("liquidity()")


def words(data: str) -> list[int]:
    payload = data[2:] if data.startswith("0x") else data
    if len(payload) % 64 != 0:
        raise ValueError("ABI response is not word aligned")
    return [int(payload[index : index + 64], 16) for index in range(0, len(payload), 64)]


def signed(value: int, bits: int) -> int:
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >= 1 << (bits - 1) else value


def decode_slot0(data: str) -> tuple[int, int]:
    values = words(data)
    if len(values) < 2:
        raise ValueError("slot0 response is incomplete")
    return values[0], signed(values[1], 24)


async def read_v3_state(provider: object, pool: PoolDefinition, observed_at: datetime) -> V3StateSnapshot:
    """Read sqrt price, tick, and active liquidity from a V3 pool."""

    slot0_result = await provider.eth_call(pool.address, SLOT0_SELECTOR)
    liquidity_result = await provider.eth_call(pool.address, LIQUIDITY_SELECTOR)
    sqrt_price_x96, tick = decode_slot0(slot0_result)
    liquidity_values = words(liquidity_result)
    if not liquidity_values:
        raise ValueError("liquidity response is empty")
    return V3StateSnapshot(
        pool_id=pool.pool_id,
        chain_id=pool.chain_id,
        observed_at=observed_at,
        sqrt_price_x96=sqrt_price_x96,
        tick=tick,
        active_liquidity=liquidity_values[0],
    )


def price_token1_per_token0(
    sqrt_price_x96: int, token0_decimals: int, token1_decimals: int
) -> float:
    """Convert Q64.96 sqrt price into human-readable token1/token0 price."""

    raw_price = (sqrt_price_x96 * sqrt_price_x96) / 2**192
    return raw_price * 10**token0_decimals / 10**token1_decimals

