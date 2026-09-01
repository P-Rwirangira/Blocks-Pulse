# Architecture Rules and Patterns

## System boundary

The system follows this direction:

```text
RPC and logs -> ingestion -> validation -> normalized facts -> features
             -> anomaly detection -> incidents -> approved AI tools -> analyst UI
```

Dependencies flow toward stable domain data. The AI layer may consume approved analytical tools, but it must not become the source of truth.

## Required boundaries

### Ingestion

Responsible for transport, retries, batching, endpoint failover, and raw capture. It must not contain dashboard formatting or LLM prompting.

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
