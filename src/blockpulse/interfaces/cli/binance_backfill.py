"""Restartable historical Binance Spot kline backfill."""

import argparse
import asyncio
import json
from datetime import UTC, date, datetime, timedelta

from blockpulse.infrastructure.config.settings import get_settings
from blockpulse.infrastructure.database.repositories import BinanceKlineRepository, Database
from blockpulse.market_data.adapters.binance.spot import BinanceSpotClient


def interval_delta(interval: str) -> timedelta:
    """Translate the supported Binance interval notation into a cursor step."""

    units = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
    if len(interval) < 2 or interval[-1] not in units or not interval[:-1].isdigit():
        raise ValueError(f"unsupported Binance interval: {interval}")
    return timedelta(**{units[interval[-1]]: int(interval[:-1])})


async def backfill_symbol(
    client: BinanceSpotClient,
    repository: BinanceKlineRepository,
    symbol: str,
    interval: str,
    start_time: datetime,
    end_time: datetime,
    limit: int,
) -> tuple[int, int]:
    current = await repository.latest_open_time(symbol, interval)
    next_start = max(start_time, current + interval_delta(interval)) if current else start_time
    inserted = 0
    pages = 0
    step = interval_delta(interval)
    while next_start < end_time:
        rows = await client.klines(symbol, interval, next_start, end_time, limit)
        pages += 1
        if not rows:
            break
        inserted += await repository.add_many(rows)
        last_open = max(row.open_time for row in rows)
        next_start = last_open + step
        if len(rows) < limit:
            break
    return pages, inserted


async def run(symbols: list[str], interval: str, start_time: datetime, end_time: datetime) -> int:
    settings = get_settings()
    database = Database(settings.database_url)
    await database.create_schema()
    client = BinanceSpotClient(str(settings.binance_base_url), settings.rpc_timeout_seconds)
    try:
        async with database.sessions() as session:
            repository = BinanceKlineRepository(session)
            for symbol in symbols:
                pages, inserted = await backfill_symbol(
                    client,
                    repository,
                    symbol.upper(),
                    interval,
                    start_time,
                    end_time,
                    settings.binance_kline_limit,
                )
                print(f"symbol={symbol.upper()} interval={interval} pages={pages} inserted={inserted}")
        return 0
    finally:
        await database.close()


def main() -> None:
    settings = get_settings()
    configured = json.loads(settings.binance_symbols_json)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", action="append", dest="symbols")
    parser.add_argument("--interval", default=settings.binance_interval)
    parser.add_argument("--start-date", default="2023-11-18")
    parser.add_argument("--end-date", default=date.today().isoformat())
    args = parser.parse_args()
    symbols = args.symbols or configured
    if not symbols or not all(isinstance(symbol, str) and symbol.strip() for symbol in symbols):
        raise ValueError("configure at least one Binance symbol")
    start = datetime.combine(date.fromisoformat(args.start_date), datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(
        date.fromisoformat(args.end_date) + timedelta(days=1), datetime.min.time(), tzinfo=UTC
    )
    raise SystemExit(asyncio.run(run(symbols, args.interval, start, end)))


if __name__ == "__main__":
    main()
