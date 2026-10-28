# Phase 6: Incidents and grounded investigation

Phase 6 turns versioned anomaly scores into operator-facing incidents without
making a model score or an LLM response the source of truth.

## Flow

```text
AnomalyScore
    -> IncidentService.open_from_score()
    -> stable fingerprint and incident projection
    -> EvidencePackageBuilder
    -> bounded read-only tools
    -> optional AIInvestigationResponse
    -> AIResponseValidator
    -> analyst presentation
```

## Incident lifecycle

Incidents are grouped deterministically by chain, entity, severity, and sorted
drivers. Valid transitions are explicit:

```text
open -> investigating -> acknowledged -> resolved
  |          |              |             
  +-------> suppressed <----+-------------
```

Every accepted transition stores an append-only status-change record with actor,
timestamp, and reason. The API persists the projection and audit event in one
transaction. Resolved incidents cannot be reopened by accident.

## Evidence contract

`EvidencePackage` contains only typed records already selected by the application:
anomaly scores, feature snapshots, quality warnings, detector metadata, and
explicit unknowns. Package and evidence IDs are deterministic, so a replay can
produce the same investigation input.

## AI safety boundary

The AI layer receives package data through `ReadOnlyToolRegistry`. It cannot issue
SQL or mutate repositories. Each material claim must cite package evidence. A
numeric claim must match a cited `value` or `score`, and responses must disclose
quality warnings. An accepted response is marked `grounded=True`; this flag is a
validation result, not a claim that the explanation proves root cause.

`AIInteractionAudit` stores only a prompt hash, model version, tool names, latency,
validation state, incident ID, and timestamp. Prompt contents and secrets are not
stored. `AIValidationEvaluator` runs deterministic regression cases for valid
citations, missing evidence, quality disclosure, and unsupported numeric claims.

## API surface

- `GET /api/v1/incidents?chain_id=&limit=` lists incident projections.
- `GET /api/v1/incidents/{incident_id}/evidence` returns typed evidence.
- `GET /api/v1/incidents/{incident_id}/timeline` returns status history.
- `POST /api/v1/incidents/{incident_id}/transition` applies one validated status change.

The incident tables are introduced by migration `0009_incidents` and are also
included in the test database metadata for isolated integration tests.

## Verification

Run `python -m pytest tests -q`. The suite covers deterministic grouping,
transition rejection, evidence idempotency, package quality warnings, allow-listed
tools, unsupported evidence references, and unsupported numerical AI claims.
