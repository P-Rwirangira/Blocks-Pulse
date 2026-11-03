import json
from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_grafana_dashboards_are_valid_json() -> None:
    dashboards = list((ROOT / "monitoring" / "grafana" / "dashboards").glob("*.json"))
    assert len(dashboards) == 6
    for dashboard in dashboards:
        payload = json.loads(dashboard.read_text(encoding="utf-8"))
        assert payload["uid"].startswith("blockpulse-")
        assert payload["panels"]


def test_prometheus_and_grafana_provisioning_reference_services() -> None:
    prometheus = (ROOT / "monitoring" / "prometheus" / "prometheus.yml").read_text()
    datasource = (ROOT / "monitoring" / "grafana" / "provisioning" / "datasources" / "prometheus.yml").read_text()
    assert "blockpulse:8000" in prometheus
    assert "http://prometheus:9090" in datasource
