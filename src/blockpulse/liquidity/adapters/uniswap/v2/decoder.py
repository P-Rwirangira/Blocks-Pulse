"""Uniswap V2 log collection and event normalization."""

from datetime import datetime

from eth_utils import keccak

from blockpulse.domain.models import PoolDefinition, PoolEvent
from blockpulse.infrastructure.rpc.jsonrpc import RawLog


def event_topic(signature: str) -> str:
    """Return the canonical Keccak topic for an event signature."""

    return "0x" + keccak(text=signature).hex()


V2_SWAP_TOPIC = event_topic("Swap(address,uint256,uint256,uint256,uint256,address)")
V2_SYNC_TOPIC = event_topic("Sync(uint112,uint112)")


def _words(data: str) -> list[int]:
    payload = data[2:] if data.startswith("0x") else data
    if len(payload) % 64 != 0:
        raise ValueError("event data is not word aligned")
    return [int(payload[index : index + 64], 16) for index in range(0, len(payload), 64)]


def decode_v2_log(log: RawLog, pool: PoolDefinition, occurred_at: datetime) -> PoolEvent:
    """Decode a V2 Swap or Sync log into a normalized event."""

    topic = log.topics[0].lower()
    values = _words(log.data)
    if topic == V2_SWAP_TOPIC:
        if len(values) != 4:
            raise ValueError("V2 Swap event must contain four data words")
        event_type = "swap"
        amount0 = (values[0] - values[2]) / 10**pool.token0_decimals
        amount1 = (values[1] - values[3]) / 10**pool.token1_decimals
        reserve0 = reserve1 = None
    elif topic == V2_SYNC_TOPIC:
        if len(values) != 2:
            raise ValueError("V2 Sync event must contain two data words")
        event_type = "sync"
        amount0 = amount1 = None
        reserve0 = values[0] / 10**pool.token0_decimals
        reserve1 = values[1] / 10**pool.token1_decimals
    else:
        raise ValueError(f"unsupported V2 event topic: {topic}")

    event_id = f"{pool.chain_id}:{log.transaction_hash}:{log.log_index}"
    return PoolEvent(
        event_id=event_id,
        pool_id=pool.pool_id,
        chain_id=pool.chain_id,
        block_number=log.block_number,
        block_hash=log.block_hash,
        transaction_hash=log.transaction_hash,
        log_index=log.log_index,
        event_type=event_type,
        occurred_at=occurred_at,
        amount0=amount0,
        amount1=amount1,
        reserve0=reserve0,
        reserve1=reserve1,
    )


class PoolLogCollector:
    """Collect and decode V2 logs for one configured pool."""

    def __init__(self, provider: object) -> None:
        self.provider = provider

    async def collect_v2(
        self,
        pool: PoolDefinition,
        from_block: int,
        to_block: int,
        occurred_at: datetime,
    ) -> list[PoolEvent]:
        raw_logs = await self.provider.get_logs(
            pool.address, from_block, to_block, [V2_SWAP_TOPIC, V2_SYNC_TOPIC]
        )
        return [decode_v2_log(log, pool, occurred_at) for log in raw_logs]
