"""Stable domain objects used across adapters and application services."""

from datetime import datetime
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
    latency_ms: float = Field(ge=0)
    success: bool
    latest_block_number: int | None = Field(default=None, ge=0)
    error_type: str | None = None


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
