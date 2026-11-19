"""SQLAlchemy persistence for Phase 1 observations."""

from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256

from sqlalchemy import BIGINT, JSON, DateTime, Float, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from blockpulse.domain.models import (
    AnomalyScore,
    AIInteractionAudit,
    BinanceKline,
    FeatureSnapshot,
    HealthMetric,
    Incident,
    IncidentEvidence,
    IncidentStatusChange,
    HistoricalBlock,
    ModelEvaluation,
    PoolEvent,
    RpcObservation,
)
from blockpulse.chain_health.application.quality import ObservationQualityReport


class Base(DeclarativeBase):
    """Base for persistent models."""


class RpcObservationRow(Base):
    """Append-only RPC observation record."""

    __tablename__ = "rpc_observations"

    observation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    endpoint_name: Mapped[str] = mapped_column(String(100), index=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float)
    success: Mapped[bool]
    latest_block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latest_block_hash: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latest_parent_hash: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class HistoricalBlockRow(Base):
    """Sampled historical chain-state fact with raw RPC provenance."""

    __tablename__ = "historical_blocks"

    block_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    block_number: Mapped[int] = mapped_column(BIGINT, index=True)
    block_hash: Mapped[str] = mapped_column(String(100))
    parent_hash: Mapped[str | None] = mapped_column(String(100), nullable=True)
    block_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    transaction_count: Mapped[int] = mapped_column(BIGINT)
    gas_used: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    gas_limit: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    base_fee_per_gas: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON)


class HistoricalBackfillCursorRow(Base):
    """Restart cursor for one bounded historical backfill."""

    __tablename__ = "historical_backfill_cursors"

    backfill_key: Mapped[str] = mapped_column(String(160), primary_key=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sample_minutes: Mapped[int] = mapped_column(Integer)
    last_block_number: Mapped[int] = mapped_column(BIGINT)


class PoolEventRow(Base):
    """Append-only normalized pool event record."""

    __tablename__ = "pool_events"

    event_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    pool_id: Mapped[str] = mapped_column(String(120), index=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    block_number: Mapped[int] = mapped_column(Integer, index=True)
    block_hash: Mapped[str] = mapped_column(String(100))
    transaction_hash: Mapped[str] = mapped_column(String(100))
    log_index: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(30), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    amount0: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount1: Mapped[float | None] = mapped_column(Float, nullable=True)
    reserve0: Mapped[float | None] = mapped_column(Float, nullable=True)
    reserve1: Mapped[float | None] = mapped_column(Float, nullable=True)
    sqrt_price_x96: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_liquidity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tick_lower: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tick_upper: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PoolCursorRow(Base):
    """Last successfully processed confirmed block for one pool."""

    __tablename__ = "pool_cursors"

    pool_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    last_processed_block: Mapped[int] = mapped_column(Integer)


class BinanceKlineRow(Base):
    """Normalized Binance Spot candle with its original public API row."""

    __tablename__ = "binance_klines"

    symbol: Mapped[str] = mapped_column(String(30), primary_key=True)
    interval: Mapped[str] = mapped_column(String(10), primary_key=True)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    quote_volume: Mapped[float] = mapped_column(Float)
    trade_count: Mapped[int] = mapped_column(BIGINT)
    taker_buy_volume: Mapped[float] = mapped_column(Float)
    taker_buy_quote_volume: Mapped[float] = mapped_column(Float)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    raw_payload: Mapped[list] = mapped_column(JSON)


class HealthMetricRow(Base):
    """Persisted derived chain-health metric."""

    __tablename__ = "health_metrics"

    metric_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    window_minutes: Mapped[int] = mapped_column(Integer)
    request_count: Mapped[int] = mapped_column(Integer)
    error_rate: Mapped[float] = mapped_column(Float)
    p95_latency_ms: Mapped[float] = mapped_column(Float)
    latest_block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_disagreement: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))


class ObservationQualityRow(Base):
    """Persisted data-quality result for an observation review."""

    __tablename__ = "observation_quality"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    observation_count: Mapped[int] = mapped_column(Integer)
    stale: Mapped[bool]
    duplicate_count: Mapped[int] = mapped_column(Integer)
    gap_count: Mapped[int] = mapped_column(Integer)
    issues: Mapped[list] = mapped_column(JSON)


class FeatureSnapshotRow(Base):
    """Persisted versioned ML feature value."""

    __tablename__ = "feature_snapshots"

    feature_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    feature_name: Mapped[str] = mapped_column(String(100), index=True)
    feature_version: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(160), index=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    window_minutes: Mapped[int] = mapped_column(Integer)
    value: Mapped[float] = mapped_column(Float)
    source_observation_ids: Mapped[list] = mapped_column(JSON)
    quality_status: Mapped[str] = mapped_column(String(30))


class AnomalyScoreRow(Base):
    """Persisted detector output with feature evidence."""

    __tablename__ = "anomaly_scores"

    anomaly_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    detector_name: Mapped[str] = mapped_column(String(80), index=True)
    detector_version: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(160), index=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    score: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(20))
    drivers: Mapped[list] = mapped_column(JSON)
    feature_ids: Mapped[list] = mapped_column(JSON)
    quality_status: Mapped[str] = mapped_column(String(30))


class ModelEvaluationRow(Base):
    """Persisted detector evaluation result."""

    __tablename__ = "model_evaluations"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    detector_name: Mapped[str] = mapped_column(String(80), index=True)
    detector_version: Mapped[str] = mapped_column(String(40), index=True)
    feature_version: Mapped[str] = mapped_column(String(40), index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    train_count: Mapped[int] = mapped_column(Integer)
    validation_count: Mapped[int] = mapped_column(Integer)
    test_count: Mapped[int] = mapped_column(Integer)
    precision: Mapped[float] = mapped_column(Float)
    recall: Mapped[float] = mapped_column(Float)
    false_positive_rate: Mapped[float] = mapped_column(Float)
    detection_delay_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    parameters: Mapped[dict] = mapped_column(JSON)


class IncidentRow(Base):
    """Operator incident projection with a stable grouping fingerprint."""

    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(240))
    anomaly_event_id: Mapped[str] = mapped_column(String(64), index=True)
    anomaly_score_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    evidence_ids: Mapped[list] = mapped_column(JSON)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class IncidentEvidenceRow(Base):
    """Typed, immutable reference to an evidence record."""

    __tablename__ = "incident_evidence"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True)
    evidence_type: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str] = mapped_column(String(160), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    summary: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict] = mapped_column(JSON)


class IncidentStatusChangeRow(Base):
    """Append-only incident lifecycle audit record."""

    __tablename__ = "incident_status_changes"

    change_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True)
    from_status: Mapped[str] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AIInteractionAuditRow(Base):
    """Privacy-safe AI invocation metadata; prompt contents are never stored."""

    __tablename__ = "ai_interaction_audits"

    interaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True)
    model_version: Mapped[str] = mapped_column(String(80), index=True)
    prompt_hash: Mapped[str] = mapped_column(String(64))
    tool_calls: Mapped[list] = mapped_column(JSON)
    latency_ms: Mapped[float] = mapped_column(Float)
    validation_state: Mapped[str] = mapped_column(String(30), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


def observation_id(observation: RpcObservation) -> str:
    """Build a deterministic identity for idempotent writes."""

    value = "|".join(
        [
            observation.endpoint_name,
            str(observation.chain_id),
            observation.observed_at.isoformat(),
            str(observation.attempt),
        ]
    )
    return sha256(value.encode("utf-8")).hexdigest()


def historical_block_id(block: HistoricalBlock) -> str:
    """Build an idempotent identity from chain and canonical block identity."""

    return f"{block.chain_id}:{block.block_number}:{block.block_hash}"


def metric_id(metric: HealthMetric) -> str:
    """Build a stable identity for a derived metric snapshot."""

    value = f"{metric.chain_id}|{metric.measured_at.isoformat()}|{metric.window_minutes}"
    return sha256(value.encode("utf-8")).hexdigest()


def quality_report_id(report: ObservationQualityReport) -> str:
    """Build a stable identity for a quality review."""

    value = "|".join(
        [report.checked_at.isoformat(), str(report.observation_count), *report.issues]
    )
    return sha256(value.encode("utf-8")).hexdigest()


class ObservationRepository:
    """Repository implementing idempotent observation persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, observations: Sequence[RpcObservation]) -> int:
        """Insert observations, ignoring deterministic duplicates."""

        inserted = 0
        for observation in observations:
            key = observation_id(observation)
            existing = await self.session.get(RpcObservationRow, key)
            if existing is not None:
                continue
            self.session.add(
                RpcObservationRow(
                    observation_id=key,
                    endpoint_name=observation.endpoint_name,
                    chain_id=observation.chain_id,
                    observed_at=observation.observed_at,
                    attempt=observation.attempt,
                    latency_ms=observation.latency_ms,
                    success=observation.success,
                    latest_block_number=observation.latest_block_number,
                    latest_block_hash=observation.latest_block_hash,
                    latest_parent_hash=observation.latest_parent_hash,
                    error_type=observation.error_type,
                    raw_payload=observation.raw_payload,
                )
            )
            inserted += 1
        await self.session.commit()
        return inserted

    async def recent(self, chain_id: int, limit: int = 100) -> list[RpcObservationRow]:
        """Return recent observations for one chain, newest first."""

        result = await self.session.scalars(
            select(RpcObservationRow)
            .where(RpcObservationRow.chain_id == chain_id)
            .order_by(RpcObservationRow.observed_at.desc())
            .limit(limit)
        )
        return list(result)


class HistoricalBlockRepository:
    """Repository for append-only historical block facts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, block: HistoricalBlock) -> bool:
        key = historical_block_id(block)
        if await self.session.get(HistoricalBlockRow, key) is not None:
            return False
        self.session.add(
            HistoricalBlockRow(
                block_id=key,
                chain_id=block.chain_id,
                block_number=block.block_number,
                block_hash=block.block_hash,
                parent_hash=block.parent_hash,
                block_timestamp=block.block_timestamp,
                transaction_count=block.transaction_count,
                gas_used=block.gas_used,
                gas_limit=block.gas_limit,
                base_fee_per_gas=block.base_fee_per_gas,
                collected_at=block.collected_at,
                source=block.source,
                raw_payload=block.raw_payload,
            )
        )
        await self.session.commit()
        return True


class HistoricalBackfillCursorRepository:
    """Repository for restartable date-bounded historical cursors."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> HistoricalBackfillCursorRow | None:
        return await self.session.get(HistoricalBackfillCursorRow, key)

    async def save(
        self,
        key: str,
        chain_id: int,
        start_date: datetime,
        end_date: datetime,
        sample_minutes: int,
        last_block_number: int,
    ) -> None:
        row = await self.session.get(HistoricalBackfillCursorRow, key)
        if row is None:
            self.session.add(
                HistoricalBackfillCursorRow(
                    backfill_key=key,
                    chain_id=chain_id,
                    start_date=start_date,
                    end_date=end_date,
                    sample_minutes=sample_minutes,
                    last_block_number=last_block_number,
                )
            )
        else:
            row.last_block_number = max(row.last_block_number, last_block_number)
        await self.session.commit()


class HealthMetricRepository:
    """Repository for idempotent derived health snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, metrics: Sequence[HealthMetric]) -> int:
        inserted = 0
        for metric in metrics:
            key = metric_id(metric)
            if await self.session.get(HealthMetricRow, key) is not None:
                continue
            self.session.add(
                HealthMetricRow(
                    metric_id=key,
                    chain_id=metric.chain_id,
                    measured_at=metric.measured_at,
                    window_minutes=metric.window_minutes,
                    request_count=metric.request_count,
                    error_rate=metric.error_rate,
                    p95_latency_ms=metric.p95_latency_ms,
                    latest_block_number=metric.latest_block_number,
                    block_disagreement=metric.block_disagreement,
                    status=metric.status.value,
                )
            )
            inserted += 1
        await self.session.commit()
        return inserted

    async def recent(self, chain_id: int, limit: int = 100) -> list[HealthMetricRow]:
        result = await self.session.scalars(
            select(HealthMetricRow)
            .where(HealthMetricRow.chain_id == chain_id)
            .order_by(HealthMetricRow.measured_at.desc())
            .limit(limit)
        )
        return list(result)


class ObservationQualityRepository:
    """Repository for idempotent data-quality reports."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, report: ObservationQualityReport) -> bool:
        key = quality_report_id(report)
        if await self.session.get(ObservationQualityRow, key) is not None:
            return False
        self.session.add(
            ObservationQualityRow(
                report_id=key,
                checked_at=report.checked_at,
                observation_count=report.observation_count,
                stale=report.stale,
                duplicate_count=report.duplicate_count,
                gap_count=report.gap_count,
                issues=list(report.issues),
            )
        )
        await self.session.commit()
        return True

    async def recent(self, limit: int = 100) -> list[ObservationQualityRow]:
        result = await self.session.scalars(
            select(ObservationQualityRow)
            .order_by(ObservationQualityRow.checked_at.desc())
            .limit(limit)
        )
        return list(result)


class FeatureRepository:
    """Repository for idempotent, traceable feature snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, features: Sequence[FeatureSnapshot]) -> int:
        inserted = 0
        for feature in features:
            if await self.session.get(FeatureSnapshotRow, feature.feature_id) is not None:
                continue
            self.session.add(
                FeatureSnapshotRow(
                    feature_id=feature.feature_id,
                    feature_name=feature.feature_name,
                    feature_version=feature.feature_version,
                    entity_type=feature.entity_type,
                    entity_id=feature.entity_id,
                    chain_id=feature.chain_id,
                    measured_at=feature.measured_at,
                    window_minutes=feature.window_minutes,
                    value=feature.value,
                    source_observation_ids=feature.source_observation_ids,
                    quality_status=feature.quality_status,
                )
            )
            inserted += 1
        await self.session.commit()
        return inserted

    async def recent(self, entity_id: str, limit: int = 500) -> list[FeatureSnapshotRow]:
        result = await self.session.scalars(
            select(FeatureSnapshotRow)
            .where(FeatureSnapshotRow.entity_id == entity_id)
            .order_by(FeatureSnapshotRow.measured_at.desc())
            .limit(limit)
        )
        return list(result)


class AnomalyRepository:
    """Repository for idempotent anomaly detector outputs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, anomalies: Sequence[AnomalyScore]) -> int:
        inserted = 0
        for anomaly in anomalies:
            if await self.session.get(AnomalyScoreRow, anomaly.anomaly_id) is not None:
                continue
            self.session.add(
                AnomalyScoreRow(
                    anomaly_id=anomaly.anomaly_id,
                    detector_name=anomaly.detector_name,
                    detector_version=anomaly.detector_version,
                    entity_type=anomaly.entity_type,
                    entity_id=anomaly.entity_id,
                    chain_id=anomaly.chain_id,
                    detected_at=anomaly.detected_at,
                    score=anomaly.score,
                    severity=anomaly.severity.value,
                    drivers=anomaly.drivers,
                    feature_ids=anomaly.feature_ids,
                    quality_status=anomaly.quality_status,
                )
            )
            inserted += 1
        await self.session.commit()
        return inserted

    async def recent(self, entity_id: str, limit: int = 100) -> list[AnomalyScoreRow]:
        result = await self.session.scalars(
            select(AnomalyScoreRow)
            .where(AnomalyScoreRow.entity_id == entity_id)
            .order_by(AnomalyScoreRow.detected_at.desc())
            .limit(limit)
        )
        return list(result)


class EvaluationRepository:
    """Repository for immutable model-evaluation records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, evaluation: ModelEvaluation) -> bool:
        if await self.session.get(ModelEvaluationRow, evaluation.run_id) is not None:
            return False
        self.session.add(
            ModelEvaluationRow(
                run_id=evaluation.run_id,
                detector_name=evaluation.detector_name,
                detector_version=evaluation.detector_version,
                feature_version=evaluation.feature_version,
                evaluated_at=evaluation.evaluated_at,
                train_count=evaluation.train_count,
                validation_count=evaluation.validation_count,
                test_count=evaluation.test_count,
                precision=evaluation.precision,
                recall=evaluation.recall,
                false_positive_rate=evaluation.false_positive_rate,
                detection_delay_seconds=evaluation.detection_delay_seconds,
                parameters=evaluation.parameters,
            )
        )
        await self.session.commit()
        return True


class IncidentRepository:
    """Repository for idempotent incidents and append-only evidence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, incident: Incident) -> bool:
        if await self.session.get(IncidentRow, incident.incident_id) is not None:
            return False
        self.session.add(
            IncidentRow(
                incident_id=incident.incident_id,
                chain_id=incident.chain_id,
                created_at=incident.created_at,
                status=incident.status.value,
                severity=incident.severity.value,
                title=incident.title,
                anomaly_event_id=incident.anomaly_event_id,
                anomaly_score_id=incident.anomaly_score_id,
                evidence_ids=incident.evidence_ids,
                fingerprint=incident.fingerprint,
            )
        )
        await self.session.commit()
        return True

    async def recent(self, chain_id: int | None = None, limit: int = 100) -> list[IncidentRow]:
        statement = select(IncidentRow).order_by(IncidentRow.created_at.desc()).limit(limit)
        if chain_id is not None:
            statement = statement.where(IncidentRow.chain_id == chain_id)
        result = await self.session.scalars(statement)
        return list(result)

    async def get(self, incident_id: str) -> IncidentRow | None:
        return await self.session.get(IncidentRow, incident_id)

    async def apply_transition(self, incident: Incident, change: IncidentStatusChange) -> bool:
        """Persist a validated projection update and its audit event atomically."""

        row = await self.session.get(IncidentRow, incident.incident_id)
        if row is None or row.status != change.from_status.value:
            return False
        if await self.session.get(IncidentStatusChangeRow, change.change_id) is not None:
            return False
        row.status = change.to_status.value
        self.session.add(
            IncidentStatusChangeRow(
                change_id=change.change_id,
                incident_id=change.incident_id,
                from_status=change.from_status.value,
                to_status=change.to_status.value,
                changed_at=change.changed_at,
                actor=change.actor,
                reason=change.reason,
            )
        )
        await self.session.commit()
        return True

    async def add_evidence(self, evidence: IncidentEvidence) -> bool:
        if await self.session.get(IncidentEvidenceRow, evidence.evidence_id) is not None:
            return False
        self.session.add(
            IncidentEvidenceRow(
                evidence_id=evidence.evidence_id,
                incident_id=evidence.incident_id,
                evidence_type=evidence.evidence_type,
                source_id=evidence.source_id,
                observed_at=evidence.observed_at,
                summary=evidence.summary,
                payload=evidence.payload,
            )
        )
        await self.session.commit()
        return True

    async def evidence(self, incident_id: str, limit: int = 500) -> list[IncidentEvidenceRow]:
        result = await self.session.scalars(
            select(IncidentEvidenceRow)
            .where(IncidentEvidenceRow.incident_id == incident_id)
            .order_by(IncidentEvidenceRow.observed_at.desc())
            .limit(limit)
        )
        return list(result)

    async def add_status_change(self, change: IncidentStatusChange) -> bool:
        if await self.session.get(IncidentStatusChangeRow, change.change_id) is not None:
            return False
        self.session.add(
            IncidentStatusChangeRow(
                change_id=change.change_id,
                incident_id=change.incident_id,
                from_status=change.from_status.value,
                to_status=change.to_status.value,
                changed_at=change.changed_at,
                actor=change.actor,
                reason=change.reason,
            )
        )
        await self.session.commit()
        return True

    async def status_history(self, incident_id: str) -> list[IncidentStatusChangeRow]:
        result = await self.session.scalars(
            select(IncidentStatusChangeRow)
            .where(IncidentStatusChangeRow.incident_id == incident_id)
            .order_by(IncidentStatusChangeRow.changed_at.asc())
        )
        return list(result)


class AIInteractionAuditRepository:
    """Repository for immutable, secret-free AI audit records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, audit: AIInteractionAudit) -> bool:
        if await self.session.get(AIInteractionAuditRow, audit.interaction_id) is not None:
            return False
        self.session.add(
            AIInteractionAuditRow(
                interaction_id=audit.interaction_id,
                incident_id=audit.incident_id,
                model_version=audit.model_version,
                prompt_hash=audit.prompt_hash,
                tool_calls=audit.tool_calls,
                latency_ms=audit.latency_ms,
                validation_state=audit.validation_state,
                created_at=audit.created_at,
            )
        )
        await self.session.commit()
        return True

    async def recent(self, incident_id: str, limit: int = 100) -> list[AIInteractionAuditRow]:
        result = await self.session.scalars(
            select(AIInteractionAuditRow)
            .where(AIInteractionAuditRow.incident_id == incident_id)
            .order_by(AIInteractionAuditRow.created_at.desc())
            .limit(limit)
        )
        return list(result)


class PoolEventRepository:
    """Repository implementing idempotent normalized event persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, events: Sequence[PoolEvent]) -> int:
        """Insert normalized events and ignore duplicate event identities."""

        inserted = 0
        for event in events:
            if await self.session.get(PoolEventRow, event.event_id) is not None:
                continue
            self.session.add(
                PoolEventRow(
                    event_id=event.event_id,
                    pool_id=event.pool_id,
                    chain_id=event.chain_id,
                    block_number=event.block_number,
                    block_hash=event.block_hash,
                    transaction_hash=event.transaction_hash,
                    log_index=event.log_index,
                    event_type=event.event_type,
                    occurred_at=event.occurred_at,
                    amount0=event.amount0,
                    amount1=event.amount1,
                    reserve0=event.reserve0,
                    reserve1=event.reserve1,
                    sqrt_price_x96=(str(event.sqrt_price_x96) if event.sqrt_price_x96 is not None else None),
                    tick=event.tick,
                    active_liquidity=(str(event.active_liquidity) if event.active_liquidity is not None else None),
                    tick_lower=event.tick_lower,
                    tick_upper=event.tick_upper,
                )
            )
            inserted += 1
        await self.session.commit()
        return inserted

    async def recent(self, pool_id: str, limit: int = 500) -> list[PoolEventRow]:
        """Return recent events for a pool, newest first."""

        result = await self.session.scalars(
            select(PoolEventRow)
            .where(PoolEventRow.pool_id == pool_id)
            .order_by(PoolEventRow.occurred_at.desc(), PoolEventRow.log_index.desc())
            .limit(limit)
        )
        return list(result)


class PoolCursorRepository:
    """Repository for restartable pool block-range cursors."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, pool_id: str) -> int:
        row = await self.session.get(PoolCursorRow, pool_id)
        return row.last_processed_block if row else -1

    async def advance(self, pool_id: str, block_number: int) -> None:
        row = await self.session.get(PoolCursorRow, pool_id)
        if row is None:
            self.session.add(PoolCursorRow(pool_id=pool_id, last_processed_block=block_number))
        elif block_number > row.last_processed_block:
            row.last_processed_block = block_number
            await self.session.commit()


class BinanceKlineRepository:
    """Repository for idempotent Binance candle persistence and cursors."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, klines: Sequence[BinanceKline]) -> int:
        inserted = 0
        for kline in klines:
            identity = {
                "symbol": kline.symbol,
                "interval": kline.interval,
                "open_time": kline.open_time,
            }
            if await self.session.get(BinanceKlineRow, identity) is not None:
                continue
            self.session.add(
                BinanceKlineRow(
                    **identity,
                    close_time=kline.close_time,
                    open_price=kline.open_price,
                    high_price=kline.high_price,
                    low_price=kline.low_price,
                    close_price=kline.close_price,
                    volume=kline.volume,
                    quote_volume=kline.quote_volume,
                    trade_count=kline.trade_count,
                    taker_buy_volume=kline.taker_buy_volume,
                    taker_buy_quote_volume=kline.taker_buy_quote_volume,
                    collected_at=kline.collected_at,
                    source=kline.source,
                    raw_payload=kline.raw_payload,
                )
            )
            inserted += 1
        await self.session.commit()
        return inserted

    async def latest_open_time(self, symbol: str, interval: str) -> datetime | None:
        result = await self.session.scalar(
            select(BinanceKlineRow.open_time)
            .where(BinanceKlineRow.symbol == symbol, BinanceKlineRow.interval == interval)
            .order_by(BinanceKlineRow.open_time.desc())
            .limit(1)
        )
        return result

    async def recent(self, symbol: str, interval: str, limit: int = 500) -> list[BinanceKlineRow]:
        result = await self.session.scalars(
            select(BinanceKlineRow)
            .where(BinanceKlineRow.symbol == symbol, BinanceKlineRow.interval == interval)
            .order_by(BinanceKlineRow.open_time.desc())
            .limit(limit)
        )
        return list(result)


class Database:
    """Own the async engine and session factory."""

    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(url)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_schema(self) -> None:
        """Create an ad hoc schema only for SQLite development databases.

        PostgreSQL schemas are owned by Alembic so workers cannot race migrations.
        """

        if self.engine.url.get_backend_name() != "sqlite":
            return
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()
