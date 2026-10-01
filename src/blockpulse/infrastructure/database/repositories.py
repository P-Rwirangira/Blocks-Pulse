"""SQLAlchemy persistence for Phase 1 observations."""

from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256

from sqlalchemy import DateTime, Float, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from blockpulse.domain.models import PoolEvent, RpcObservation


class Base(DeclarativeBase):
    """Base for persistent models."""


class RpcObservationRow(Base):
    """Append-only RPC observation record."""

    __tablename__ = "rpc_observations"

    observation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    endpoint_name: Mapped[str] = mapped_column(String(100), index=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latency_ms: Mapped[float] = mapped_column(Float)
    success: Mapped[bool]
    latest_block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)


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


def observation_id(observation: RpcObservation) -> str:
    """Build a deterministic identity for idempotent writes."""

    value = "|".join(
        [
            observation.endpoint_name,
            str(observation.chain_id),
            observation.observed_at.isoformat(),
        ]
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
                    latency_ms=observation.latency_ms,
                    success=observation.success,
                    latest_block_number=observation.latest_block_number,
                    error_type=observation.error_type,
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
