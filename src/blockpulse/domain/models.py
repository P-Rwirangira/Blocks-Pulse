"""Stable domain objects used across adapters and application services."""

from datetime import datetime
from typing import Any
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class RpcObservation(BaseModel):
    """One measured JSON-RPC request result."""

    model_config = ConfigDict(frozen=True)

    endpoint_name: str
    chain_id: int = Field(gt=0)
    observed_at: datetime
    attempt: int = Field(default=0, ge=0)
    latency_ms: float = Field(ge=0)
    success: bool
    latest_block_number: int | None = Field(default=None, ge=0)
    latest_block_hash: str | None = None
    latest_parent_hash: str | None = None
    error_type: str | None = None
    raw_payload: dict[str, Any] | None = None


class ReorgSignal(BaseModel):
    """Evidence that one endpoint observed a conflicting chain head."""

    endpoint_name: str
    chain_id: int = Field(gt=0)
    detected_at: datetime
    block_number: int = Field(ge=0)
    previous_block_number: int = Field(ge=0)
    previous_block_hash: str | None = None
    observed_block_hash: str | None = None
    reason: str


class HealthMetric(BaseModel):
    """Aggregated health state for a chain and observation window."""

    chain_id: int = Field(gt=0)
    measured_at: datetime
    window_minutes: int = Field(gt=0)
    request_count: int = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    p95_latency_ms: float = Field(ge=0)
    latest_block_number: int | None = Field(default=None, ge=0)
    block_disagreement: int = Field(default=0, ge=0)
    status: HealthStatus


class AnomalyEvent(BaseModel):
    """A reproducible health anomaly derived from stored metrics."""

    event_id: str
    chain_id: int = Field(gt=0)
    detected_at: datetime
    score: float = Field(ge=0, le=1)
    status: HealthStatus
    drivers: list[str]
    metric: HealthMetric


class Incident(BaseModel):
    """Operator-facing lifecycle record for an anomaly."""

    incident_id: str
    chain_id: int = Field(gt=0)
    created_at: datetime
    status: IncidentStatus = IncidentStatus.OPEN
    severity: HealthStatus
    title: str
    anomaly_event_id: str
    evidence_ids: list[str] = Field(default_factory=list)


class ChainHealthSummary(BaseModel):
    """Named health summary for one configured chain."""

    name: str
    metric: HealthMetric


class HealthOverview(BaseModel):
    """Cross-chain health view for the operator dashboard."""

    measured_at: datetime
    chains: list[ChainHealthSummary]
    healthiest_chain: str | None = None
    least_healthy_chain: str | None = None


class PoolDefinition(BaseModel):
    """Configured pool identity and token metadata."""

    pool_id: str
    chain_id: int = Field(gt=0)
    address: str
    protocol: str = "uniswap"
    version: str = "v2"
    token0_symbol: str
    token1_symbol: str
    token0_decimals: int = Field(ge=0, le=255)
    token1_decimals: int = Field(ge=0, le=255)
    start_block: int = Field(default=0, ge=0)
    fee_tier: int | None = Field(default=None, ge=0, le=1_000_000)
    tick_spacing: int | None = Field(default=None, gt=0)


class PoolEvent(BaseModel):
    """Normalized immutable event emitted by a monitored pool."""

    event_id: str
    pool_id: str
    chain_id: int = Field(gt=0)
    block_number: int = Field(ge=0)
    block_hash: str
    transaction_hash: str
    log_index: int = Field(ge=0)
    event_type: str
    occurred_at: datetime
    amount0: float | None = None
    amount1: float | None = None
    reserve0: float | None = None
    reserve1: float | None = None
    sqrt_price_x96: int | None = Field(default=None, ge=0)
    tick: int | None = None
    active_liquidity: int | None = Field(default=None, ge=0)
    tick_lower: int | None = None
    tick_upper: int | None = None


class PoolMetric(BaseModel):
    """Time-windowed monitoring metrics for one pool."""

    pool_id: str
    chain_id: int = Field(gt=0)
    measured_at: datetime
    window_minutes: int = Field(gt=0)
    swap_count: int = Field(ge=0)
    volume_token0: float = Field(ge=0)
    volume_token1: float = Field(ge=0)
    latest_reserve0: float | None = Field(default=None, ge=0)
    latest_reserve1: float | None = Field(default=None, ge=0)
    liquidity_change_pct: float | None = None
    price_token1_per_token0: float | None = Field(default=None, ge=0)
    latest_tick: int | None = None
    latest_sqrt_price_x96: int | None = Field(default=None, ge=0)
    active_liquidity: int | None = Field(default=None, ge=0)


class V3StateSnapshot(BaseModel):
    """Point-in-time state read directly from a V3 pool contract."""

    pool_id: str
    chain_id: int = Field(gt=0)
    observed_at: datetime
    sqrt_price_x96: int = Field(ge=0)
    tick: int
    active_liquidity: int = Field(ge=0)
