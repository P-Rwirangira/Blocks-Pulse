"""SQLAlchemy persistence for Phase 1 observations."""

from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256

from sqlalchemy import DateTime, Float, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from blockpulse.domain import RpcObservation


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

