# Historical block backfill

Historical block backfill provides sampled chain-state facts for ML features and
does not recreate historical RPC latency or error-rate telemetry. Those values are
only measured by the live collector.

## Run

The command uses the configured first RPC endpoint for a chain and defaults to the
September replay window in `.env`:

```powershell
docker compose run --rm blockpulse blockpulse-backfill-blocks 1 --sample-minutes 360
docker compose run --rm blockpulse blockpulse-backfill-blocks 8453 --sample-minutes 360
docker compose run --rm blockpulse blockpulse-backfill-blocks 42161 --sample-minutes 360
```

Override the date range explicitly when needed:

```powershell
docker compose run --rm blockpulse blockpulse-backfill-blocks 8453 `
  --start-date 2026-09-01 --end-date 2026-09-30 --sample-minutes 60
```

The sampler records block number, hashes, timestamp, transaction count, gas
fields, base fee, raw RPC payload, collection time, and the
`historical_backfill` source label. It uses a PostgreSQL cursor keyed by chain,
date range, and interval, so interrupted runs resume and repeated runs are
idempotent.

## Operational guidance

- Use 360 minutes for a light free-RPC backfill and 60 minutes for a denser MVP
  feature set.
- Run one chain at a time and monitor RPC provider limits.
- Check `historical_blocks` counts and date coverage before training models.
- Keep historical state features separate from live RPC health metrics.
- Never interpret `collected_at` as the historical block time; use
  `block_timestamp` for chain-time analysis.
