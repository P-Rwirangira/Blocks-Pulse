"""Prometheus metrics adapter for BlockPulse operations."""

from collections.abc import Mapping
from time import perf_counter

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class MetricsRegistry:
    """Own a private Prometheus registry to keep tests and app instances isolated."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.http_requests = Counter(
            "blockpulse_http_requests_total",
            "HTTP requests handled by BlockPulse",
            ("method", "route", "status"),
            registry=self.registry,
        )
        self.http_latency = Histogram(
            "blockpulse_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ("method", "route"),
            registry=self.registry,
        )
        self.rpc_observations = Counter(
            "blockpulse_rpc_observations_total",
            "RPC observations by outcome",
            ("chain_id", "success"),
            registry=self.registry,
        )
        self.rpc_latency = Histogram(
            "blockpulse_rpc_latency_seconds",
            "Observed RPC latency in seconds",
            ("chain_id",),
            registry=self.registry,
        )
        self.chain_health = Gauge(
            "blockpulse_chain_health_status",
            "Chain health severity as 0 healthy, 1 warning, 2 critical",
            ("chain_id",),
            registry=self.registry,
        )
        self.active_incidents = Gauge(
            "blockpulse_active_incidents",
            "Currently active incidents by severity",
            ("severity",),
            registry=self.registry,
        )
        self.anomalies = Counter(
            "blockpulse_anomalies_total",
            "Anomaly scores by severity and detector",
            ("detector", "severity"),
            registry=self.registry,
        )
        self.data_quality = Gauge(
            "blockpulse_data_quality_status",
            "Data quality state as 1 valid, 0 degraded",
            ("scope",),
            registry=self.registry,
        )
        self.collection_cycles = Counter(
            "blockpulse_collection_cycles_total",
            "Completed multi-chain collection cycles",
            registry=self.registry,
        )
        self.collection_duration = Histogram(
            "blockpulse_collection_duration_seconds",
            "Collection cycle duration in seconds",
            registry=self.registry,
        )
        self.pool_events = Counter(
            "blockpulse_pool_events_total",
            "Normalized pool events collected",
            ("pool_id", "event_type"),
            registry=self.registry,
        )
        self.binance_klines = Counter(
            "blockpulse_binance_klines_total",
            "Normalized Binance candles collected",
            ("symbol", "interval"),
            registry=self.registry,
        )
        self.binance_failures = Counter(
            "blockpulse_binance_collection_failures_total",
            "Binance collection failures",
            registry=self.registry,
        )
        self.ai_validation = Counter(
            "blockpulse_ai_validation_total",
            "AI response validation outcomes",
            ("state",),
            registry=self.registry,
        )

    def observe_http(self, method: str, route: str, status: int, duration_seconds: float) -> None:
        self.http_requests.labels(method, route, str(status)).inc()
        self.http_latency.labels(method, route).observe(duration_seconds)

    def observe_rpc(self, chain_id: int, success: bool, latency_ms: float) -> None:
        self.rpc_observations.labels(str(chain_id), str(success).lower()).inc()
        self.rpc_latency.labels(str(chain_id)).observe(latency_ms / 1000)

    def set_chain_health(self, chain_id: int, status: str) -> None:
        values = {"healthy": 0, "warning": 1, "critical": 2}
        if status not in values:
            raise ValueError(f"unknown health status: {status}")
        self.chain_health.labels(str(chain_id)).set(values[status])

    def set_active_incidents(self, counts: Mapping[str, int]) -> None:
        for severity, count in counts.items():
            self.active_incidents.labels(severity).set(count)

    def observe_anomaly(self, detector: str, severity: str) -> None:
        self.anomalies.labels(detector, severity).inc()

    def set_data_quality(self, scope: str, valid: bool) -> None:
        self.data_quality.labels(scope).set(1 if valid else 0)

    def observe_collection(self, observation_count: int, duration_ms: float) -> None:
        self.collection_cycles.inc()
        self.collection_duration.observe(duration_ms / 1000)

    def observe_pool_event(self, pool_id: str, event_type: str) -> None:
        self.pool_events.labels(pool_id, event_type).inc()

    def observe_binance_klines(self, symbol: str, interval: str, count: int) -> None:
        self.binance_klines.labels(symbol, interval).inc(count)

    def observe_binance_failure(self) -> None:
        self.binance_failures.inc()

    def observe_ai_validation(self, state: str) -> None:
        self.ai_validation.labels(state).inc()

    def render(self) -> bytes:
        return generate_latest(self.registry)

    @staticmethod
    def timer() -> "_Timer":
        return _Timer()


class _Timer:
    """Small dependency-free timer for service instrumentation."""

    def __enter__(self) -> "_Timer":
        self.started = perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        self.elapsed_seconds = perf_counter() - self.started
