from blockpulse.infrastructure.observability import MetricsRegistry
from datetime import UTC, datetime

from blockpulse.chain_health.application.quality import ObservationQualityReport, publish_quality_metrics


def test_metrics_registry_renders_stable_operational_metrics() -> None:
    metrics = MetricsRegistry()
    metrics.observe_http("GET", "/healthz", 200, 0.01)
    metrics.set_active_incidents({"critical": 2})
    metrics.observe_collection(2, 100)
    metrics.observe_binance_klines("ETHUSDT", "1h", 1)
    metrics.observe_ai_validation("accepted")
    publish_quality_metrics(
        ObservationQualityReport(datetime(2026, 9, 1, tzinfo=UTC), 1, False, 0, 0, ()),
        "chain:8453",
        metrics,
    )
    rendered = metrics.render().decode()
    assert "blockpulse_http_requests_total" in rendered
    assert "blockpulse_binance_klines_total" in rendered
    assert 'severity="critical"' in rendered
    assert "blockpulse_ai_validation_total" in rendered
    assert 'scope="chain:8453"' in rendered
