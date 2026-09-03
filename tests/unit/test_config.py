from blockpulse.config import Settings


def test_settings_have_base_defaults() -> None:
    settings = Settings()

    assert settings.base_chain_id == 8453
    assert settings.rpc_confirmations == 2
    assert settings.health_window_minutes == 15

