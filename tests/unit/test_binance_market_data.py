from datetime import UTC, datetime, timedelta

import pytest

from blockpulse.interfaces.cli.binance_backfill import interval_delta
from blockpulse.market_data.adapters.binance.spot import BinanceSpotClient


def test_binance_kline_normalization_preserves_raw_row() -> None:
    row = [
        1_700_000_000_000,
        "2000.0",
        "2100.0",
        "1900.0",
        "2050.0",
        "12.5",
        1_700_003_599_999,
        "25000.0",
        42,
        "6.2",
        "12400.0",
        "0",
    ]
    collected_at = datetime.now(UTC)
    kline = BinanceSpotClient._normalize(row, "ETHUSDT", "1h", collected_at)

    assert kline.symbol == "ETHUSDT"
    assert kline.open_price == 2000.0
    assert kline.trade_count == 42
    assert kline.raw_payload == row


@pytest.mark.parametrize(
    ("interval", "expected"),
    [("1m", timedelta(minutes=1)), ("1h", timedelta(hours=1)), ("1d", timedelta(days=1))],
)
def test_interval_delta(interval: str, expected: timedelta) -> None:
    assert interval_delta(interval) == expected


def test_interval_delta_rejects_unsupported_interval() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        interval_delta("1M")
