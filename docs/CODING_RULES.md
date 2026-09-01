# Coding Rules and Best Practices

## General

- Use clear names that describe domain meaning rather than implementation detail.
- Keep functions small and focused on one responsibility.
- Prefer explicit data structures and typed interfaces at system boundaries.
- Keep configuration separate from business logic.
- Fail loudly on invalid chain IDs, addresses, timestamps, decimals, and schema versions.
- Never silently discard malformed or incomplete blockchain observations.

## Data engineering

- Preserve raw RPC responses and request metadata before normalization.
- Make writes idempotent using stable keys such as `(chain_id, block_number, block_hash)` or event identity.
- Store timestamps in UTC and retain source timestamps where available.
- Track source endpoint, request latency, retry count, and freshness.
- Treat reorganization handling as a first-class path, not an exception-only path.
- Validate block continuity, parent hashes, token decimals, and event addresses.
- Separate Bronze/raw, Silver/normalized, and Gold/derived data layers.

## ML

- Establish a deterministic baseline before adding a learned model.
- Use time-aware train/validation splits; do not randomly leak future observations into training.
- Version features, labels, model parameters, and evaluation data.
- Store anomaly scores with model version, feature window, and top drivers.
- Report false positives, detection delay, calibration, and data-quality impact.
- Never present an anomaly score as proof of malicious activity.

## AI

- Prefer approved read-only tools over unrestricted database access.
- Validate tool names and parameters before execution.
- Pass structured evidence packages to the model.
- Validate numerical claims against tool results before showing them to users.
- Require citations or evidence IDs for material claims.
- Refuse or qualify answers when the data is stale, incomplete, or insufficient.
- Log prompts, tool calls, model version, latency, and final validation state without storing secrets.

## Testing

- Test normal paths, retries, duplicates, missing ranges, reorgs, stale data, and malformed payloads.
- Use deterministic fixtures for blockchain events and AI evaluation.
- Keep integration tests isolated from live public RPCs by default.
- Add a regression test for every bug that could recur.

## Security and operations

- Never commit API keys, private keys, wallet secrets, or personal access tokens.
- Use environment variables or a local ignored file for secrets.
- Keep production writes and transaction execution out of the MVP unless explicitly designed and reviewed.
- Add structured logs and health checks before adding complexity.
