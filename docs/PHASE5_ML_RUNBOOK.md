# Phase 5 ML Runbook

## Pipeline

```text
observations/events
  -> quality validation
  -> versioned feature snapshots
  -> aligned feature vectors
  -> deterministic baselines
  -> optional multivariate detector
  -> anomaly scores
  -> evaluation report
```

## Feature contracts

Feature snapshots include a feature name, version, entity, timestamp, window,
value, quality state, and source observation IDs. Required feature names are
aligned into `FeatureVector` rows; incomplete windows are excluded explicitly.

Implemented feature families:

- RPC error rate, P95 latency, and block disagreement.
- Pool swaps, volumes, price, liquidity, ticks, and active liquidity.
- Cross-chain asset-pair price mean and dispersion.

## Detectors

- `robust_mad`: median/MAD baseline for resistant univariate detection.
- `ewma_change_point`: abrupt regime-shift detection.
- `isolation_forest`: seeded multivariate detector over aligned vectors.

All anomaly outputs include detector name/version, score, severity, driver names,
feature IDs, and quality status. Scores are signals for investigation, not proof
of malicious activity.

## Evaluation

Use chronological train, validation, and test partitions. Random splits are not
allowed. Persist precision, recall, false-positive rate, dataset sizes, detector
parameters, feature version, and evaluation run ID.

Before enabling a detector for operator alerts, review false positives, missed
events, detection delay, and behavior under stale or incomplete data.

## Phase 5 completion checklist

- [x] Versioned feature contract and stable source identities
- [x] RPC, liquidity, and cross-chain feature generation
- [x] Feature snapshot persistence and idempotency
- [x] Aligned multivariate feature vectors
- [x] Robust MAD baseline
- [x] EWMA/change-point baseline
- [x] Seeded Isolation Forest detector
- [x] Persisted anomaly scores
- [x] Time-aware evaluation and model evaluation records
- [x] Detector execution service
