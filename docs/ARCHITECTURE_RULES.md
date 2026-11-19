# Architecture Rules and Patterns

## System boundary

The active Binance-only system follows this direction:

```text
Binance REST/WebSocket market data -> ingestion -> validation -> normalized facts -> features
             -> anomaly detection -> incidents -> approved AI tools -> analyst UI
```

Dependencies flow toward stable domain data. The AI layer may consume approved analytical tools, but it must not become the source of truth.

## Current package layout

The Python package is organized by capability and architectural role rather than by
one large collection of modules:

```text
src/blockpulse/
  domain/                  # stable entities and value objects
  shared/                  # narrow cross-cutting ports
  chain_health/            # legacy RPC health use cases and detectors
    application/
  liquidity/               # legacy on-chain pool monitoring use cases and DEX adapters
    application/
    adapters/uniswap/v2/
    adapters/uniswap/v3/
  incidents/               # incident lifecycle and evidence policy
    application/
  infrastructure/          # settings, RPC transport, persistence
    config/
    rpc/
    database/
  interfaces/               # HTTP and CLI composition boundaries
    http/
    cli/
  market_data/              # active centralized-market ingestion
    adapters/binance/
```

New behavior belongs in the capability package that owns it. Domain modules must
not import infrastructure or interface modules. Application services depend on
ports and domain models; infrastructure implements those ports; interfaces wire
the application together. The short root-level modules are compatibility facades
for existing entry points and must not be used by new internal code.

Each capability should expose small application services, keep provider-specific
logic behind adapters, and make persistence replaceable through repository ports.
Prefer composition at the HTTP/CLI boundary over global service state.

## Required boundaries

### Ingestion

Responsible for Binance transport, pagination, rate-limit handling, retry policy,
and raw capture. It must not contain dashboard formatting or LLM prompting.

### Normalization

Responsible for chain-specific decoding, decimals, timestamps, canonical identities, deduplication, and reorganization flags.

### Storage

Responsible for durable facts and derived records. Schema migrations must be explicit and reversible where practical.

### Features and models

Responsible for time windows, baselines, anomaly scores, labels, and model metadata. Models must not mutate raw or normalized facts.

### Incidents

Responsible for severity, lifecycle, evidence references, and operator status. Incident creation should be deterministic and reproducible from stored observations.

### AI tools

Responsible for validated read-only analytical operations. Tool outputs must be structured and evidence-bearing.

## Preferred patterns

- Adapter pattern for chain- or provider-specific RPC behavior.
- Repository pattern for storage access behind testable interfaces.
- Strategy pattern for anomaly detectors and severity policies.
- Event/envelope pattern for incident records and evidence packages.
- Configuration-driven registry for chains, assets, pools, and endpoints.
- Append-only raw observations with derived projections for analytics.

## Anti-patterns

- Calling an LLM directly from an ingestion worker.
- Mixing raw RPC decoding with UI-specific formatting.
- Using random train/test splits for time-series observations.
- Treating one public RPC response as authoritative without freshness checks.
- Hiding failed records with broad exception handling.
- Adding a new chain by copying and modifying an entire pipeline.
- Allowing a generated SQL query to write to the database.
