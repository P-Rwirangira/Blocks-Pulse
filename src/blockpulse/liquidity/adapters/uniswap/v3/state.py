"""Read current Uniswap V3 state from the canonical pool view methods."""

from datetime import datetime

from eth_utils import keccak

from blockpulse.domain.models import PoolDefinition, V3StateSnapshot


def selector(signature: str) -> str:
    return "0x" + keccak(text=signature)[:4].hex()


SLOT0_SELECTOR = selector("slot0()")
LIQUIDITY_SELECTOR = selector("liquidity()")
OBSERVE_SELECTOR = selector("observe(uint32[])")


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


def encode_observe(seconds_agos: list[int]) -> str:
    """Encode observe(uint32[]) for a read-only eth_call."""

    if not seconds_agos or any(value < 0 or value > 2**32 - 1 for value in seconds_agos):
        raise ValueError("seconds_agos must contain valid uint32 values")
    words_payload = [32, len(seconds_agos), *seconds_agos]
    return OBSERVE_SELECTOR + "".join(f"{value:064x}" for value in words_payload)


def decode_observe(data: str) -> tuple[list[int], list[int]]:
    """Decode the two dynamic arrays returned by observe(uint32[])."""

    values = words(data)
    if len(values) < 4:
        raise ValueError("observe response is incomplete")
    first_offset, second_offset = values[0], values[1]
    if first_offset // 32 >= len(values) or second_offset // 32 >= len(values):
        raise ValueError("observe response offsets are invalid")
    first_start = first_offset // 32
    second_start = second_offset // 32
    first_count = values[first_start]
    second_count = values[second_start]
    first = [signed(item, 56) for item in values[first_start + 1 : first_start + 1 + first_count]]
    second = values[second_start + 1 : second_start + 1 + second_count]
    if len(first) != first_count or len(second) != second_count:
        raise ValueError("observe response arrays are truncated")
    return first, second


async def read_v3_twap(provider: object, pool: PoolDefinition, seconds_ago: int) -> tuple[int, int]:
    """Return tick and seconds-per-liquidity cumulatives for a lookback."""

    result = await provider.eth_call(pool.address, encode_observe([seconds_ago, 0]))
    ticks, liquidity = decode_observe(result)
    if len(ticks) != 2 or len(liquidity) != 2:
        raise ValueError("observe response must contain two points")
    elapsed = max(seconds_ago, 1)
    return int((ticks[1] - ticks[0]) / elapsed), liquidity[1] - liquidity[0]


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
