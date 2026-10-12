"""CLI for materializing historical chain-health metrics."""

import argparse
import asyncio

from blockpulse.chain_health.application.historical_service import HistoricalHealthBackfillService
from blockpulse.infrastructure.config.settings import get_settings
from blockpulse.infrastructure.database.repositories import (
    Database,
    HealthMetricRepository,
    ObservationRepository,
)


async def backfill_health(chain_id: int, window_minutes: int) -> int:
    """Build metric snapshots for stored observations on one chain."""

    settings = get_settings()
    database = Database(settings.database_url)
    await database.create_schema()
    try:
        async with database.sessions() as session:
            built, inserted = await HistoricalHealthBackfillService(
                ObservationRepository(session), HealthMetricRepository(session)
            ).backfill_chain(chain_id, window_minutes)
        print(f"chain_id={chain_id} metrics_built={built} metrics_inserted={inserted}")
        return 0
    finally:
        await database.close()


def main() -> None:
    """Run the bounded health backfill command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chain_id", type=int)
    parser.add_argument("--window-minutes", type=int, default=15)
    arguments = parser.parse_args()
    raise SystemExit(asyncio.run(backfill_health(arguments.chain_id, arguments.window_minutes)))
