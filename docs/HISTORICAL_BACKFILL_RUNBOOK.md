# Historical market-data backfill

The active MVP uses Binance Spot klines as its source of truth. On-chain and
Uniswap backfill procedures are no longer part of the project.

## Binance kline backfill

Binance public market data is available without an API key. The backfill stores
one normalized row per `(symbol, interval, open_time)`, preserves the original
JSON array, and resumes from the latest stored candle:

```powershell
blockpulse-backfill-binance --symbol ETHUSDT --interval 1h --start-date 2023-11-18
```

Use additional symbols explicitly or configure them in `.env`:

```powershell
blockpulse-backfill-binance --symbol ETHUSDT --symbol BTCUSDT --interval 1h \
  --start-date 2023-11-18 --end-date 2026-11-18
```

One-hour candles provide a practical three-year ML baseline with approximately
26,000 rows per symbol. Use smaller intervals only when the model requires finer
microstructure detail.

## Operational guidance

- Use one-hour candles for the initial three-year training window.
- Backfill one symbol at a time and monitor Binance response limits.
- Check `binance_klines` row counts and timestamp coverage before training models.
- Keep the original `raw_payload` when exporting or transforming data.
- Use explicit `--end-date` values for reproducible historical datasets.
