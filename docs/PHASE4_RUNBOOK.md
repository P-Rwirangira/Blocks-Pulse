# Phase 4 Operations Runbook

## Startup

1. Configure RPC URLs and the database URL in `.env`.
2. Run `blockpulse-migrate` against a shared or production database.
3. Start `blockpulse-collect-loop` for continuous RPC observations.
4. Start the API and verify `/healthz` and `/readyz`.

## Historical projections

Run `blockpulse-backfill-health <chain_id> --window-minutes 15` after observations
have accumulated. The command is idempotent and only projects observations that
are already stored.

## Quality signals

Every collection cycle records a quality report containing freshness, duplicate,
and observation-gap findings. A failed or stale report is a data-quality warning;
it must not be presented as evidence of chain failure.

## Failure handling

- Retryable RPC failures use exponential backoff.
- Endpoints crossing the failure threshold open a circuit temporarily.
- A later recovery probe closes the circuit after the cooldown.
- Block rollbacks, conflicting hashes, and parent mismatches produce reorganization
  evidence for later incident processing.
- Migration failures must be fixed before starting workers; do not bypass them with
  manual table edits.

## Phase 4 completion gate

- [x] Restartable and idempotent ingestion
- [x] Retry, backoff, failover, and circuit protection
- [x] Raw response and block identity provenance
- [x] Reorganization detection
- [x] Pool and chain-health backfill projections
- [x] Freshness and completeness checks
- [x] Reversible migrations
- [x] Readiness and structured telemetry
- [ ] Run PostgreSQL integration coverage with a dedicated database before release
