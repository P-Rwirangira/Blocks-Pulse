from blockpulse.infrastructure.observability import MetricsRegistry
from blockpulse.chain_health.application.quality import publish_quality_metrics, ObservationQualityReport
from datetime import UTC, datetime


def test_metrics_registry_renders_stable_operational_metrics() -> None:
    metrics = MetricsRegistry()
    metrics.observe_http("GET", "/healthz", 200, 0.01)
    metrics.observe_rpc(8453, True, 120)
    metrics.set_chain_health(8453, "healthy")
    metrics.set_active_incidents({"critical": 2})
    metrics.observe_collection(2, 100)
    metrics.observe_pool_event("pool-1", "swap")
    metrics.observe_ai_validation("accepted")
    publish_quality_metrics(
        ObservationQualityReport(datetime(2026, 9, 1, tzinfo=UTC), 1, False, 0, 0, ()),
        "chain:8453",
        metrics,
    )
    rendered = metrics.render().decode()
    assert "blockpulse_http_requests_total" in rendered
    assert 'chain_id="8453"' in rendered
    assert "blockpulse_chain_health_status" in rendered
    assert 'severity="critical"' in rendered
    assert "blockpulse_ai_validation_total" in rendered
    assert 'scope="chain:8453"' in rendered
