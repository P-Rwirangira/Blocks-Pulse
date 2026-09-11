"""Command-line entry point for a single Phase 1 collection cycle."""

import asyncio
from datetime import UTC, datetime

from blockpulse.collection_service import CollectionService
from blockpulse.config import get_settings
from blockpulse.rpc import JsonRpcProvider
from blockpulse.storage import Database, ObservationRepository


async def collect_once() -> int:
    """Collect the configured Base RPC endpoints once."""

    settings = get_settings()
    if not settings.base_rpc_urls:
        raise RuntimeError("set BLOCKPULSE_BASE_RPC_URLS before collecting")
    database = Database(settings.database_url)
    await database.create_schema()
    providers = [
        JsonRpcProvider(
            name=f"base-{index + 1}",
            chain_id=settings.base_chain_id,
            url=str(url),
            timeout_seconds=settings.rpc_timeout_seconds,
        )
        for index, url in enumerate(settings.base_rpc_urls)
    ]
    try:
        async with database.sessions() as session:
            observations, inserted = await CollectionService(
                providers, ObservationRepository(session)
            ).collect_once(datetime.now(UTC))
        successful = sum(item.success for item in observations)
        print(f"observations={len(observations)} successful={successful} inserted={inserted}")
        return 0 if successful else 1
    finally:
        await database.close()


def main() -> None:
    """Run the one-shot collector."""

    raise SystemExit(asyncio.run(collect_once()))

