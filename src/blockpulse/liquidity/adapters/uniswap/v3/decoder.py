"""Uniswap V3 event topics and normalized decoders."""

from datetime import datetime

from eth_utils import keccak

from blockpulse.domain.models import PoolDefinition, PoolEvent
from blockpulse.infrastructure.rpc.jsonrpc import RawLog


def event_topic(signature: str) -> str:
    return "0x" + keccak(text=signature).hex()


V3_INITIALIZE_TOPIC = event_topic("Initialize(uint160,int24)")
V3_SWAP_TOPIC = event_topic("Swap(address,address,int256,int256,uint160,uint128,int24)")
V3_MINT_TOPIC = event_topic("Mint(address,address,int24,int24,uint128,uint256,uint256)")
V3_BURN_TOPIC = event_topic("Burn(address,int24,int24,uint128,uint256,uint256)")
V3_COLLECT_TOPIC = event_topic("Collect(address,address,int24,int24,uint128,uint128)")


def _words(data: str) -> list[int]:
    payload = data[2:] if data.startswith("0x") else data
    if len(payload) % 64 != 0:
        raise ValueError("event data is not word aligned")
    return [int(payload[index : index + 64], 16) for index in range(0, len(payload), 64)]


def _signed(value: int, bits: int = 256) -> int:
    value &= (1 << bits) - 1
    boundary = 1 << (bits - 1)
    return value - (1 << bits) if value >= boundary else value


def _topic_int(topic: str, bits: int = 256) -> int:
    value = int(topic, 16)
    return _signed(value, bits)


def _base(log: RawLog, pool: PoolDefinition, occurred_at: datetime, event_type: str) -> dict:
    return {
        "event_id": f"{pool.chain_id}:{log.transaction_hash}:{log.log_index}",
        "pool_id": pool.pool_id,
        "chain_id": pool.chain_id,
        "block_number": log.block_number,
        "block_hash": log.block_hash,
        "transaction_hash": log.transaction_hash,
        "log_index": log.log_index,
        "event_type": event_type,
        "occurred_at": occurred_at,
    }


def decode_v3_log(log: RawLog, pool: PoolDefinition, occurred_at: datetime) -> PoolEvent:
    """Decode one official Uniswap V3 pool event."""

    topic = log.topics[0].lower()
    values = _words(log.data)
    fields = _base(log, pool, occurred_at, "")
    if topic == V3_INITIALIZE_TOPIC:
        if len(values) != 2:
            raise ValueError("V3 Initialize event must contain two data words")
        fields.update(event_type="initialize", sqrt_price_x96=values[0], tick=_signed(values[1], 24))
    elif topic == V3_SWAP_TOPIC:
        if len(values) != 5:
            raise ValueError("V3 Swap event must contain five data words")
        fields.update(
            event_type="swap",
            amount0=float(_signed(values[0])),
            amount1=float(_signed(values[1])),
            sqrt_price_x96=values[2],
            active_liquidity=values[3],
            tick=_signed(values[4], 24),
        )
    elif topic in {V3_MINT_TOPIC, V3_BURN_TOPIC}:
        if len(log.topics) < 4 or len(values) != 3:
            raise ValueError("V3 Mint/Burn event has invalid indexed or data fields")
        fields.update(
            event_type="mint" if topic == V3_MINT_TOPIC else "burn",
            tick_lower=_topic_int(log.topics[2], 24),
            tick_upper=_topic_int(log.topics[3], 24),
            active_liquidity=values[0],
            amount0=float(values[1]),
            amount1=float(values[2]),
        )
    elif topic == V3_COLLECT_TOPIC:
        if len(log.topics) < 4 or len(values) != 3:
            raise ValueError("V3 Collect event has invalid indexed or data fields")
        fields.update(
            event_type="collect",
            tick_lower=_topic_int(log.topics[2], 24),
            tick_upper=_topic_int(log.topics[3], 24),
            amount0=float(values[1]),
            amount1=float(values[2]),
        )
    else:
        raise ValueError(f"unsupported V3 event topic: {topic}")
    return PoolEvent(**fields)


class V3PoolLogCollector:
    """Collect and decode V3 pool logs."""

    def __init__(self, provider: object) -> None:
        self.provider = provider

    async def collect(
        self, pool: PoolDefinition, from_block: int, to_block: int, occurred_at: datetime
    ) -> list[PoolEvent]:
        logs = await self.provider.get_logs(
            pool.address,
            from_block,
            to_block,
            [
                V3_INITIALIZE_TOPIC,
                V3_SWAP_TOPIC,
                V3_MINT_TOPIC,
                V3_BURN_TOPIC,
                V3_COLLECT_TOPIC,
            ],
        )
        return [decode_v3_log(log, pool, occurred_at) for log in logs]
