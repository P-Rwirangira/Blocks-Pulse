"""Application configuration loaded from environment variables."""

from datetime import date
from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RpcEndpointSettings(BaseSettings):
    """Configuration for one JSON-RPC endpoint."""

    name: str
    url: AnyHttpUrl
    timeout_seconds: float = Field(default=10.0, gt=0)


class Settings(BaseSettings):
    """Runtime settings for the Phase 1 vertical slice."""

    model_config = SettingsConfigDict(env_prefix="BLOCKPULSE_", env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./blockpulse.db"
    base_chain_id: int = Field(default=8453, gt=0)
    base_rpc_urls: list[AnyHttpUrl] = Field(default_factory=list)
    ethereum_rpc_urls: list[AnyHttpUrl] = Field(default_factory=list)
    arbitrum_rpc_urls: list[AnyHttpUrl] = Field(default_factory=list)
    rpc_timeout_seconds: float = Field(default=10.0, gt=0)
    rpc_retries: int = Field(default=1, ge=0)
    rpc_retry_backoff_seconds: float = Field(default=0.5, ge=0)
    collection_interval_seconds: float = Field(default=30.0, gt=0)
    rpc_confirmations: int = Field(default=2, ge=0)
    health_window_minutes: int = Field(default=15, gt=0)
    metrics_port: int = Field(default=8001, gt=0, le=65535)
    collector_enabled: bool = True
    detector_enabled: bool = True
    incident_enabled: bool = True
    replay_start_date: date = date(2026, 9, 1)
    replay_end_date: date = date(2026, 9, 30)
    alertmanager_url: str | None = None
    rpc_error_rate_alert_threshold: float = Field(default=0.25, ge=0, le=1)
    rpc_p95_latency_alert_ms: float = Field(default=2_000, ge=0)
    data_stale_after_seconds: int = Field(default=120, gt=0)
    incident_alert_severities: list[str] = Field(default_factory=lambda: ["critical"])
    worker_poll_seconds: float = Field(default=30, gt=0)
    pools_json: str = "[]"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one cached settings instance for the process."""

    return Settings()
