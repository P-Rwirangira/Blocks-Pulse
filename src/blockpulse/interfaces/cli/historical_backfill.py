"""CLI for bounded historical block sampling."""

import argparse
import asyncio
from datetime import date

from blockpulse.chain_health.application.historical_backfill import HistoricalBlockBackfillService
from blockpulse.infrastructure.config.chains import enabled_chains, providers_for_chain
from blockpulse.infrastructure.config.settings import get_settings
from blockpulse.infrastructure.database.repositories import (
    Database,
    HistoricalBackfillCursorRepository,
    HistoricalBlockRepository,
)


async def run(chain_id: int, start_date: date, end_date: date, sample_minutes: int) -> int:
    settings = get_settings()
    chain = next((item for item in enabled_chains(settings) if item.chain_id == chain_id), None)
    if chain is None:
        raise ValueError(f"chain {chain_id} has no configured RPC URL")
    providers = providers_for_chain(chain, settings.rpc_timeout_seconds)
    if not providers:
        raise ValueError(f"chain {chain_id} has no configured RPC URL")

    database = Database(settings.database_url)
    await database.create_schema()
    try:
        async with database.sessions() as session:
            result = await HistoricalBlockBackfillService(
                providers[0],
                HistoricalBlockRepository(session),
                HistoricalBackfillCursorRepository(session),
            ).backfill(start_date, end_date, sample_minutes)
        print(f"chain_id={chain_id} fetched={result[0]} inserted={result[1]}")
        return 0
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chain_id", type=int)
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--sample-minutes", type=int, default=60)
    args = parser.parse_args()
    settings = get_settings()
    start = args.start_date or settings.replay_start_date
    end = args.end_date or settings.replay_end_date
    raise SystemExit(asyncio.run(run(args.chain_id, start, end, args.sample_minutes)))
