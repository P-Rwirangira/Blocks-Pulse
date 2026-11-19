# BlockPulse

BlockPulse is a Binance Spot market-health, liquidity-proxy, anomaly-detection, and evidence-grounded AI investigation platform.

The current repository begins with the expanded product prototype and the engineering rules that will guide the implementation. The MVP intentionally excludes profitability, trade execution, bridges, and autonomous actions.

## Phase 1 status

The active MVP now uses Binance public Spot market data only. It stores normalized candlesticks, preserves the raw API rows, supports restartable historical backfills, and exposes market data for ML, anomaly detection, Grafana, and evidence-grounded AI. The former RPC and Uniswap modules remain as compatibility code and are not part of the active collector.

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
docker compose up -d postgres
blockpulse-migrate
blockpulse-collect-binance-loop
blockpulse-backfill-binance --symbol ETHUSDT --interval 1h --start-date 2023-11-18
uvicorn blockpulse.api:app --reload
```

Binance public market-data endpoints do not require an API key. Tests use deterministic fixtures and SQLite, so they do not require live market access.

Production or shared environments should run `blockpulse-migrate` before starting
the collector or API. Schema changes belong in `migrations/versions/` and must be
reversible; test databases may continue to use automatic schema creation.

## Binance MVP

Configure symbols in `.env` with `BLOCKPULSE_BINANCE_SYMBOLS_JSON`. The default is
`ETHUSDT` at one-hour resolution. Historical klines are fetched in pages, written
idempotently to `binance_klines`, and can be resumed after interruption:

```powershell
blockpulse-backfill-binance --symbol ETHUSDT --interval 1h --start-date 2023-11-18
blockpulse-collect-binance-loop
```

The API endpoint `/api/v1/markets/ETHUSDT/klines?interval=1h&limit=500` returns
normalized candles with source timestamps and raw evidence. Binance klines provide
open, high, low, close, volume, quote volume, and trade counts; they are not an
on-chain liquidity pool or order-book snapshot.

## Phase 4 status

Phase 4 ingestion reliability is implemented. The system now provides retry
backoff, endpoint circuit breaking, continuous collection, raw RPC payload and
block-identity capture, reorganization signals, restartable pool backfill,
historical health projection, persisted quality reports, endpoint scoring,
readiness checks, structured collection counters, and reversible migrations.

Use `blockpulse-backfill-health <chain_id>` to materialize historical metrics from
stored observations. This is deliberately a projection of captured data; it does
not claim that a normal public RPC can reconstruct unavailable historical state.

Legacy chain and pool collectors remain available for migration and comparison, but
the active Docker collector is Binance-only.

## MVP direction

- Monitor selected Binance Spot symbols such as ETHUSDT and BTCUSDT.
- Track price, volume, volatility, trade-count, and liquidity-proxy behavior.
- Detect stale candles, volume shocks, volatility shifts, and price dislocations.
- Detect unusual behavior with robust baselines and later multivariate models.
- Explain incidents through approved read-only analytical tools and verified evidence.

## Repository guide

- `AGENTS.md` - project-wide contribution rules.
- `docs/CODING_RULES.md` - programming, data, ML, AI, testing, and security practices.
- `docs/ARCHITECTURE_RULES.md` - system boundaries and preferred patterns.
- `docs/SELF_IMPROVING.md` - process for turning failures into durable controls.
- `BlockPulse_Project_Prototype_Expanded.pdf` - full visual product and system blueprint.
- `docs/PHASE5_ML_RUNBOOK.md` - feature, detector, evaluation, and ML operating rules.
- `docs/PHASE7_GRAFANA_RUNBOOK.md` - Prometheus metrics, Grafana dashboards, and local operations.

## Prototype data note

Charts in the prototype are illustrative demo telemetry. They are not live measurements and must be replaced or clearly labelled when the implementation begins.

Phase 5 now provides the first end-to-end ML foundation: traceable features,
deterministic baselines, a seeded multivariate detector, persisted anomaly scores,
and time-aware evaluation records. Phase 6 now adds deterministic incident
lifecycle, evidence packages, read-only investigation tools, grounded AI
validation, operator APIs, and privacy-safe AI audit records. Phase 7 adds a
Grafana-only observability layer with Prometheus metrics and reproducible local
dashboard provisioning for chain health, liquidity, incidents, ML, and data
quality; no custom frontend is required.
