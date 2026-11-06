from datetime import date

from blockpulse.infrastructure.config.settings import Settings


def test_phase8_settings_have_reproducible_september_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.replay_start_date == date(2026, 9, 1)
    assert settings.replay_end_date == date(2026, 9, 30)
    assert settings.rpc_error_rate_alert_threshold == 0.25
    assert settings.incident_alert_severities == ["critical"]


def test_settings_parse_phase8_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("BLOCKPULSE_COLLECTOR_ENABLED", "false")
    monkeypatch.setenv("BLOCKPULSE_REPLAY_START_DATE", "2026-09-07")
    monkeypatch.setenv("BLOCKPULSE_INCIDENT_ALERT_SEVERITIES", '["warning", "critical"]')
    settings = Settings(_env_file=None)

    assert settings.collector_enabled is False
    assert settings.replay_start_date == date(2026, 9, 7)
    assert settings.incident_alert_severities == ["warning", "critical"]
