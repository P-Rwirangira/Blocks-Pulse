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


class IncidentTransition(BaseModel):
    """Auditable status change performed by an operator or workflow."""

    incident_id: str
    from_status: IncidentStatus
    to_status: IncidentStatus
    changed_at: datetime
    actor: str
    reason: str | None = None


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


class HistoricalBlock(BaseModel):
    """Sampled historical block header and activity facts."""

    model_config = ConfigDict(frozen=True)

    chain_id: int = Field(gt=0)
    block_number: int = Field(ge=0)
    block_hash: str
    parent_hash: str | None = None
    block_timestamp: datetime
    transaction_count: int = Field(ge=0)
    gas_used: int | None = Field(default=None, ge=0)
    gas_limit: int | None = Field(default=None, ge=0)
    base_fee_per_gas: int | None = Field(default=None, ge=0)
    collected_at: datetime
    source: str = "historical_backfill"
    raw_payload: dict[str, Any]


class BinanceKline(BaseModel):
    """One normalized Binance Spot candlestick with its raw source row."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1)
    interval: str = Field(min_length=1)
    open_time: datetime
    close_time: datetime
    open_price: float = Field(ge=0)
    high_price: float = Field(ge=0)
    low_price: float = Field(ge=0)
    close_price: float = Field(ge=0)
    volume: float = Field(ge=0)
    quote_volume: float = Field(ge=0)
    trade_count: int = Field(ge=0)
    taker_buy_volume: float = Field(ge=0)
    taker_buy_quote_volume: float = Field(ge=0)
    collected_at: datetime
    source: str = "binance_spot_rest"
    raw_payload: list[Any]


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


class EndpointHealthScore(BaseModel):
    """Provider-level reliability score for one observation window."""

    endpoint_name: str
    chain_id: int = Field(gt=0)
    request_count: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=1)
    average_latency_ms: float = Field(ge=0)
    consecutive_failures: int = Field(ge=0)
    score: float = Field(ge=0, le=1)
    status: HealthStatus


class FeatureSnapshot(BaseModel):
    """Versioned, traceable feature value for an ML input window."""

    feature_id: str
    feature_name: str
    feature_version: str
    entity_type: str
    entity_id: str
    # Zero denotes a deliberately cross-chain feature scope.
    chain_id: int = Field(ge=0)
    measured_at: datetime
    window_minutes: int = Field(gt=0)
    value: float
    source_observation_ids: list[str] = Field(min_length=1)
    quality_status: str = "valid"


class FeatureVector(BaseModel):
    """Aligned multivariate feature row for model training or scoring."""

    vector_id: str
    entity_type: str
    entity_id: str
    chain_id: int = Field(ge=0)
    measured_at: datetime
    feature_values: dict[str, float]
    feature_ids: dict[str, str]
    quality_status: str = "valid"


class AnomalyScore(BaseModel):
    """Versioned anomaly result with traceable feature evidence."""

    anomaly_id: str
    detector_name: str
    detector_version: str
    entity_type: str
    entity_id: str
    chain_id: int = Field(ge=0)
    detected_at: datetime
    score: float = Field(ge=0, le=1)
    severity: HealthStatus
    drivers: list[str] = Field(min_length=1)
    feature_ids: list[str] = Field(min_length=1)
    quality_status: str = "valid"


class ModelEvaluation(BaseModel):
    """Immutable evaluation record for a detector version."""

    run_id: str
    detector_name: str
    detector_version: str
    feature_version: str
    evaluated_at: datetime
    train_count: int = Field(ge=0)
    validation_count: int = Field(ge=0)
    test_count: int = Field(ge=0)
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    false_positive_rate: float = Field(ge=0, le=1)
    detection_delay_seconds: float | None = Field(default=None, ge=0)
    parameters: dict[str, Any]


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
    anomaly_score_id: str | None = None
    fingerprint: str | None = None


class IncidentEvidence(BaseModel):
    """A typed reference to a stored fact used to explain an incident."""

    evidence_id: str
    incident_id: str
    evidence_type: str
    source_id: str
    observed_at: datetime
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class IncidentStatusChange(BaseModel):
    """Append-only lifecycle event for an incident."""

    change_id: str
    incident_id: str
    from_status: IncidentStatus
    to_status: IncidentStatus
    changed_at: datetime
    actor: str
    reason: str | None = None


class EvidencePackage(BaseModel):
    """Bounded facts supplied to an analyst or AI explanation layer."""

    package_id: str
    incident_id: str
    generated_at: datetime
    evidence: list[IncidentEvidence] = Field(default_factory=list)
    detector_name: str | None = None
    detector_version: str | None = None
    anomaly_score: float | None = Field(default=None, ge=0, le=1)
    quality_warnings: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class AIClaim(BaseModel):
    """One model-generated statement that must point to package evidence."""

    text: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    numeric_value: float | None = None


class AIInvestigationResponse(BaseModel):
    """Structured, qualified AI output accepted by the presentation layer."""

    incident_id: str
    summary: str = Field(min_length=1)
    claims: list[AIClaim] = Field(default_factory=list)
    possible_explanations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    unknowns: list[str] = Field(default_factory=list)
    grounded: bool = False


class AIInteractionAudit(BaseModel):
    """Privacy-safe audit record for one bounded AI investigation."""

    interaction_id: str
    incident_id: str
    model_version: str
    prompt_hash: str
    tool_calls: list[str] = Field(default_factory=list)
    latency_ms: float = Field(ge=0)
    validation_state: str
    created_at: datetime
