"""SQLAlchemy persistence for Phase 1 observations."""

from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256

from sqlalchemy import JSON, DateTime, Float, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from blockpulse.domain.models import AnomalyScore, FeatureSnapshot, HealthMetric, PoolEvent, RpcObservation
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


class Database:
    """Own the async engine and session factory."""

    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(url)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()
