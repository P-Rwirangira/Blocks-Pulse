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
