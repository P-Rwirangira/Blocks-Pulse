# Ingestion Operations Runbook

## Startup

1. Configure Binance symbols and the database URL in `.env`.
2. Run `blockpulse-migrate` against a shared or production database.
3. Start `blockpulse-collect-binance-loop` for continuous kline collection.
4. Start the API and verify `/healthz` and `/readyz`.

## Quality signals

Every collection cycle records counters and failures. A failed or stale candle
must be treated as a data-quality warning, not as evidence of a market event.

## Failure handling

- Retryable Binance failures use bounded retry and backoff.
- Repeated failures are exposed through collector metrics and logs.
- Backfill writes are idempotent and can be resumed after interruption.
- Migration failures must be fixed before starting workers; do not bypass them with
  manual table edits.

## Phase 4 completion gate

- [x] Restartable and idempotent ingestion
- [x] Retry and backoff for Binance requests
- [x] Raw response provenance
- [x] Restartable kline backfill
- [x] Freshness and completeness checks
- [x] Reversible migrations
- [x] Readiness and structured telemetry
- [ ] Run PostgreSQL integration coverage with a dedicated database before release
