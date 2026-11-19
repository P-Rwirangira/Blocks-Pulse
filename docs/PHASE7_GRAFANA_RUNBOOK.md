# Phase 7: Grafana observability runbook

Phase 7 provides the operator view through Grafana and Prometheus. BlockPulse
application logic remains Python-only; no custom frontend is required.

## Local startup

From the repository root:

```text
docker compose up --build
```

Services:

- BlockPulse API: `http://localhost:8000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Grafana credentials: `admin` / `blockpulse` for the local demo only

The API container applies Alembic migrations before starting Uvicorn. Prometheus
scrapes `/metrics` every 15 seconds. Grafana provisions the Prometheus datasource
and dashboards automatically.

The long-running collector exposes its own metrics endpoint on port `8001`; the
Prometheus configuration scrapes both the API and collector targets. This keeps
collection and API telemetry separate when they run in different processes.

## Dashboards

| Dashboard | Purpose | Main signals |
| --- | --- | --- |
| BlockPulse Overview | Overall service view | HTTP traffic, Binance collection, latency, anomalies |
| Incidents | Operator workload | active incidents, anomaly rate, HTTP failures |
| ML Anomalies | Detector behavior | detector rate and severity distribution |
| Binance Market Data | Binance ingestion operations | candles, collection cycles, collection failures |
| Data Quality | Trustworthiness of derived views | valid/degraded quality state by scope |

Dashboard JSON is provisioned from `monitoring/grafana/dashboards/` and must stay
version-controlled. Every panel uses a named `blockpulse_*` metric or a PromQL
expression derived from one.

## Metrics boundary

`MetricsRegistry` owns a private Prometheus registry. Application services depend
on narrow metrics protocols, while the Prometheus client remains in infrastructure.
This keeps business logic testable and avoids coupling domain code to Grafana.

Important metrics include:

- `blockpulse_http_requests_total`
- `blockpulse_http_request_duration_seconds`
- `blockpulse_anomalies_total`
- `blockpulse_active_incidents`
- `blockpulse_data_quality_status`
- `blockpulse_binance_klines_total`
- `blockpulse_binance_collection_failures_total`
- `blockpulse_collection_cycles_total`
- `blockpulse_collection_duration_seconds`
- `blockpulse_ai_validation_total`

## Verification

Run:

```text
python -m pytest tests -q
```

The integration suite verifies the Binance collector and API composition with
deterministic fixtures; it does not require a live exchange connection.

Validate dashboard JSON before committing changes. If Docker is available, run
`docker compose config` and then `docker compose up --build` to verify service
startup and Prometheus scraping. The Grafana stack is a local demonstration
environment; change credentials and add authentication before deployment.
