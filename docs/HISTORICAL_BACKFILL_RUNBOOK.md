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

## Pool event backfill

The local `.env.example` contains a small benchmark registry of verified Uniswap
V3 WETH/USDC pools on Ethereum, Base, and Arbitrum. The ignored local `.env`
should contain the same registry before running the pool backfill:

```powershell
docker compose run --rm blockpulse blockpulse-backfill-pools --max-range-blocks 1000
```

Use `--pool-id` to replay one pool at a time. The command stores normalized
`swap`, `mint`, `burn`, `collect`, and `initialize` events plus their block and
transaction identities. V3 swap events carry the on-chain square-root price,
active liquidity, and tick at the swap. The cursor is per pool and the event
identity makes reruns idempotent.

This event backfill does not reconstruct TVL by itself. TVL and zero-activity
intervals require periodic token-balance and V3 state snapshots, which are the
next pool-data layer.
