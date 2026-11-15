"""Restartable historical backfill for configured Uniswap pool events."""

import argparse
import asyncio
from datetime import UTC, datetime

import httpx

from blockpulse.infrastructure.config.chains import enabled_chains, providers_for_chain
from blockpulse.infrastructure.config.pools import configured_pools
from blockpulse.infrastructure.config.settings import get_settings
from blockpulse.infrastructure.database.repositories import (
    Database,
    PoolCursorRepository,
    PoolEventRepository,
)
from blockpulse.infrastructure.rpc.jsonrpc import RpcProviderError
from blockpulse.liquidity.application.backfill import PoolBackfillService
from blockpulse.liquidity.application.collection import PoolCollectionService


async def run(pool_id: str | None, target_block: int | None, max_range_blocks: int) -> int:
    settings = get_settings()
    pools = configured_pools(settings)
    selected = tuple(pool for pool in pools if pool_id is None or pool.pool_id == pool_id)
    if not selected:
        raise ValueError("no configured pools matched; set BLOCKPULSE_POOLS_JSON first")

    chains = {chain.chain_id: chain for chain in enabled_chains(settings)}
    database = Database(settings.database_url)
    await database.create_schema()
    try:
        async with database.sessions() as session:
            for pool in selected:
                chain = chains.get(pool.chain_id)
                if chain is None:
                    raise ValueError(f"pool {pool.pool_id} has no configured chain RPC")
                providers = providers_for_chain(chain, settings.rpc_timeout_seconds)
                if not providers:
                    raise ValueError(f"pool {pool.pool_id} has no configured chain RPC")
                result = None
                last_error: Exception | None = None
                for provider in providers:
                    try:
                        head = await provider.observe_latest_block(datetime.now(UTC))
                        if not head.success or head.latest_block_number is None:
                            raise RuntimeError(f"could not read the latest block for {pool.pool_id}")
                        requested_target = (
                            target_block if target_block is not None else head.latest_block_number
                        )
                        result = await PoolBackfillService(
                            PoolCollectionService(
                                provider,
                                PoolEventRepository(session),
                                PoolCursorRepository(session),
                                confirmations=settings.rpc_confirmations,
                                max_range_blocks=max_range_blocks,
                            )
                        ).backfill(pool, requested_target, datetime.now(UTC))
                        break
                    except (httpx.HTTPError, RpcProviderError) as exc:
                        last_error = exc
                        print(f"pool_id={pool.pool_id} endpoint_failed={provider.name} error={type(exc).__name__}")
                if result is None:
                    if last_error is not None:
                        raise last_error
                    raise RuntimeError(f"could not backfill {pool.pool_id}")
                print(
                    f"pool_id={result.pool_id} target_block={result.target_block} "
                    f"final_block={result.final_block} cycles={result.cycles} "
                    f"events_seen={result.events_seen} events_inserted={result.events_inserted}"
                )
        return 0
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-id")
    parser.add_argument("--target-block", type=int)
    parser.add_argument("--max-range-blocks", type=int, default=1_000)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.pool_id, args.target_block, args.max_range_blocks)))


if __name__ == "__main__":
    main()
