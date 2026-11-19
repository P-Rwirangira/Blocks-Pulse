"""Public Binance Spot REST adapter for historical and recent klines."""

from datetime import UTC, datetime
from typing import Any

import httpx

from blockpulse.domain.models import BinanceKline


class BinanceMarketDataError(RuntimeError):
    """Raised when Binance returns an invalid or unsuccessful market-data response."""


class BinanceSpotClient:
    """Fetch public Binance Spot market data without authentication."""

    def __init__(self, base_url: str = "https://data-api.binance.vision", timeout_seconds: float = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def klines(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1_000,
    ) -> list[BinanceKline]:
        """Fetch one bounded, chronologically ordered kline page."""

        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError("Binance kline boundaries must be timezone-aware")
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        if not 1 <= limit <= 1_000:
            raise ValueError("Binance kline limit must be between 1 and 1000")
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol must not be empty")
        params = {
            "symbol": normalized_symbol,
            "interval": interval,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "limit": limit,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/api/v3/klines", params=params)
            response.raise_for_status()
            payload: Any = response.json()
        if not isinstance(payload, list):
            raise BinanceMarketDataError("Binance klines response was not a list")
        collected_at = datetime.now(UTC)
        return [self._normalize(row, normalized_symbol, interval, collected_at) for row in payload]

    @staticmethod
    def _normalize(row: Any, symbol: str, interval: str, collected_at: datetime) -> BinanceKline:
        if not isinstance(row, list) or len(row) < 12:
            raise BinanceMarketDataError("Binance kline row is incomplete")

        def timestamp(value: Any) -> datetime:
            if not isinstance(value, (int, float)):
                raise BinanceMarketDataError("Binance kline timestamp is invalid")
            return datetime.fromtimestamp(value / 1000, tz=UTC)

        def number(value: Any) -> float:
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise BinanceMarketDataError("Binance kline numeric field is invalid") from exc

        return BinanceKline(
            symbol=symbol,
            interval=interval,
            open_time=timestamp(row[0]),
            close_time=timestamp(row[6]),
            open_price=number(row[1]),
            high_price=number(row[2]),
            low_price=number(row[3]),
            close_price=number(row[4]),
            volume=number(row[5]),
            quote_volume=number(row[7]),
            trade_count=int(row[8]),
            taker_buy_volume=number(row[9]),
            taker_buy_quote_volume=number(row[10]),
            collected_at=collected_at,
            raw_payload=row,
        )
