"""Continuous Binance Spot kline collector."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

from blockpulse.infrastructure.config.settings import get_settings
from blockpulse.infrastructure.database.repositories import BinanceKlineRepository, Database
from blockpulse.infrastructure.observability import MetricsRegistry
from blockpulse.market_data.adapters.binance.spot import BinanceSpotClient
from prometheus_client.exposition import start_http_server


async def collect_once(metrics: MetricsRegistry | None = None) -> int:
    settings = get_settings()
    symbols = json.loads(settings.binance_symbols_json)
    if not symbols:
        raise RuntimeError("configure at least one Binance symbol")
    interval = settings.binance_interval
    database = Database(settings.database_url)
    await database.create_schema()
    client = BinanceSpotClient(str(settings.binance_base_url), settings.rpc_timeout_seconds)
    try:
        async with database.sessions() as session:
            repository = BinanceKlineRepository(session)
            end = datetime.now(UTC)
            start = end - timedelta(days=2)
            inserted = 0
            for symbol in symbols:
                rows = await client.klines(symbol, interval, start, end, settings.binance_kline_limit)
                inserted += await repository.add_many(rows)
                if metrics is not None:
                    metrics.observe_binance_klines(symbol.upper(), interval, len(rows))
        print(f"symbols={len(symbols)} interval={interval} inserted={inserted}")
        return 0
    finally:
        await database.close()


async def collect_forever() -> None:
    settings = get_settings()
    metrics = MetricsRegistry()
    start_http_server(settings.metrics_port, registry=metrics.registry)
    while True:
        try:
            await collect_once(metrics)
        except Exception as exc:  # keep the worker alive; next cycle retries the source
            metrics.observe_binance_failure()
            print(f"binance_collection_failed={type(exc).__name__}: {exc}")
        await asyncio.sleep(settings.collection_interval_seconds)


def main() -> None:
    raise SystemExit(asyncio.run(collect_once()))


def worker_main() -> None:
    raise SystemExit(asyncio.run(collect_forever()))
