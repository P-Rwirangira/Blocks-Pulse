"""Command-line entry point for a single Phase 1 collection cycle."""

import asyncio
from datetime import UTC, datetime

from blockpulse.chain_registry import enabled_chains, providers_for_chain
from blockpulse.collection_service import MultiChainCollectionService
from blockpulse.config import get_settings
from blockpulse.storage import Database, ObservationRepository


async def collect_once() -> int:
    """Collect the configured Base RPC endpoints once."""

    settings = get_settings()
    chains = enabled_chains(settings)
    if not chains:
        raise RuntimeError("configure at least one chain RPC URL before collecting")
    database = Database(settings.database_url)
    await database.create_schema()
    providers_by_chain = {
        chain: providers_for_chain(chain, settings.rpc_timeout_seconds) for chain in chains
    }
    try:
        async with database.sessions() as session:
            observations_by_chain, inserted = await MultiChainCollectionService(
                providers_by_chain, ObservationRepository(session)
            ).collect_once(datetime.now(UTC))
        observations = [item for values in observations_by_chain.values() for item in values]
        successful = sum(item.success for item in observations)
        print(
            f"chains={len(observations_by_chain)} observations={len(observations)} "
            f"successful={successful} inserted={inserted}"
        )
        return 0 if successful else 1
    finally:
        await database.close()


def main() -> None:
    """Run the one-shot collector."""

    raise SystemExit(asyncio.run(collect_once()))
