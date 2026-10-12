"""Command-line entry point for a single Phase 1 collection cycle."""

import asyncio
from datetime import UTC, datetime, timedelta

from blockpulse.infrastructure.config.chains import enabled_chains, providers_for_chain
from blockpulse.infrastructure.config.settings import get_settings
from blockpulse.infrastructure.database.repositories import Database, ObservationRepository
from blockpulse.infrastructure.database.repositories import ObservationQualityRepository
from blockpulse.chain_health.application.quality import assess_observation_quality
from blockpulse.chain_health.application.collection import MultiChainCollectionService
from blockpulse.chain_health.application.worker import CollectionWorker


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
                providers_by_chain,
                ObservationRepository(session),
                retries=settings.rpc_retries,
                retry_backoff_seconds=settings.rpc_retry_backoff_seconds,
            ).collect_once(datetime.now(UTC))
            quality = assess_observation_quality(
                [item for values in observations_by_chain.values() for item in values],
                checked_at=datetime.now(UTC),
                expected_interval=timedelta(seconds=settings.collection_interval_seconds),
            )
            await ObservationQualityRepository(session).add(quality)
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


async def collect_forever() -> None:
    """Run collection cycles until the process is cancelled."""

    settings = get_settings()
    await CollectionWorker(collect_once, settings.collection_interval_seconds).run()


def worker_main() -> None:
    """Run the continuous collector command."""

    raise SystemExit(asyncio.run(collect_forever()))
