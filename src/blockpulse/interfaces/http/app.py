"""FastAPI surface for Phase 1 health data."""

from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from blockpulse.chain_health.application.service import HealthService
from blockpulse.chain_health.application.endpoint_health import calculate_endpoint_health
from blockpulse.domain.models import (
    EndpointHealthScore,
    HealthMetric,
    HealthOverview,
    Incident,
    IncidentStatus,
    PoolDefinition,
    PoolEvent,
    PoolMetric,
    RpcObservation,
)
from blockpulse.infrastructure.config.chains import configured_chains
from blockpulse.infrastructure.config.pools import configured_pools
from blockpulse.infrastructure.config.settings import get_settings
from blockpulse.infrastructure.database.repositories import (
    Database,
    IncidentRepository,
    ObservationRepository,
    PoolEventRepository,
)
from blockpulse.liquidity.application.service import PoolService
from blockpulse.incidents.application.service import IncidentService


class IncidentTransitionRequest(BaseModel):
    """Explicit operator intent for one lifecycle change."""

    status: IncidentStatus
    actor: str = Field(min_length=1, max_length=120)
    reason: str | None = Field(default=None, max_length=500)


def create_app(database: Database | None = None) -> FastAPI:
    """Create the API application with an injectable database dependency."""

    settings = get_settings()
    app = FastAPI(title="BlockPulse API", version="0.1.0")
    app.state.database = database or Database(settings.database_url)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        """Confirm that the API can reach its configured database."""

        try:
            async with app.state.database.sessions() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="database is not ready") from exc
        return {"status": "ready"}

    @app.get("/api/v1/chains")
    async def chains() -> list[dict[str, object]]:
        return [
            {
                "name": chain.name,
                "chain_id": chain.chain_id,
                "configured": bool(chain.rpc_urls),
                "endpoint_count": len(chain.rpc_urls),
            }
            for chain in configured_chains(settings)
        ]

    @app.get("/api/v1/chains/{chain_id}/endpoints/health", response_model=list[EndpointHealthScore])
    async def endpoint_health(chain_id: int) -> list[EndpointHealthScore]:
        async with app.state.database.sessions() as session:
            rows = await ObservationRepository(session).recent(chain_id, limit=500)
        observations = [
            RpcObservation(
                endpoint_name=row.endpoint_name,
                chain_id=row.chain_id,
                observed_at=row.observed_at,
                attempt=row.attempt,
                latency_ms=row.latency_ms,
                success=row.success,
                latest_block_number=row.latest_block_number,
                latest_block_hash=row.latest_block_hash,
                latest_parent_hash=row.latest_parent_hash,
                error_type=row.error_type,
                raw_payload=row.raw_payload,
            )
            for row in rows
        ]
        return calculate_endpoint_health(observations)

    @app.get("/api/v1/chains/{chain_id}/health", response_model=HealthMetric)
    async def chain_health(chain_id: int) -> HealthMetric:
        async with app.state.database.sessions() as session:
            service = HealthService(ObservationRepository(session))
            try:
                return await service.current(chain_id, settings.health_window_minutes)
            except LookupError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/v1/overview", response_model=HealthOverview)
    async def overview() -> HealthOverview:
        async with app.state.database.sessions() as session:
            service = HealthService(ObservationRepository(session))
            return await service.overview(configured_chains(settings), settings.health_window_minutes)

    @app.get("/api/v1/incidents")
    async def incidents(
        chain_id: int | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, object]]:
        """List operator incidents through a bounded read-only projection."""

        async with app.state.database.sessions() as session:
            rows = await IncidentRepository(session).recent(chain_id=chain_id, limit=limit)
        return [
            {
                "incident_id": row.incident_id,
                "chain_id": row.chain_id,
                "created_at": row.created_at,
                "status": row.status,
                "severity": row.severity,
                "title": row.title,
                "anomaly_score_id": row.anomaly_score_id,
                "evidence_ids": row.evidence_ids,
            }
            for row in rows
        ]

    @app.get("/api/v1/incidents/{incident_id}/evidence")
    async def incident_evidence(
        incident_id: str,
        limit: int = Query(default=500, ge=1, le=1000),
    ) -> list[dict[str, object]]:
        async with app.state.database.sessions() as session:
            rows = await IncidentRepository(session).evidence(incident_id, limit=limit)
        return [
            {
                "evidence_id": row.evidence_id,
                "incident_id": row.incident_id,
                "evidence_type": row.evidence_type,
                "source_id": row.source_id,
                "observed_at": row.observed_at,
                "summary": row.summary,
                "payload": row.payload,
            }
            for row in rows
        ]

    @app.get("/api/v1/incidents/{incident_id}")
    async def incident_detail(incident_id: str) -> dict[str, object]:
        async with app.state.database.sessions() as session:
            row = await IncidentRepository(session).get(incident_id)
        if row is None:
            raise HTTPException(status_code=404, detail="incident not found")
        return {
            "incident_id": row.incident_id,
            "chain_id": row.chain_id,
            "created_at": row.created_at,
            "status": row.status,
            "severity": row.severity,
            "title": row.title,
            "anomaly_event_id": row.anomaly_event_id,
            "anomaly_score_id": row.anomaly_score_id,
            "evidence_ids": row.evidence_ids,
            "fingerprint": row.fingerprint,
        }

    @app.get("/api/v1/incidents/{incident_id}/timeline")
    async def incident_timeline(incident_id: str) -> list[dict[str, object]]:
        async with app.state.database.sessions() as session:
            rows = await IncidentRepository(session).status_history(incident_id)
        return [
            {
                "change_id": row.change_id,
                "incident_id": row.incident_id,
                "from_status": row.from_status,
                "to_status": row.to_status,
                "changed_at": row.changed_at,
                "actor": row.actor,
                "reason": row.reason,
            }
            for row in rows
        ]

    @app.post("/api/v1/incidents/{incident_id}/transition")
    async def transition_incident(
        incident_id: str,
        request: IncidentTransitionRequest,
    ) -> dict[str, object]:
        async with app.state.database.sessions() as session:
            repository = IncidentRepository(session)
            row = await repository.get(incident_id)
            if row is None:
                raise HTTPException(status_code=404, detail="incident not found")
            incident = Incident(
                incident_id=row.incident_id,
                chain_id=row.chain_id,
                created_at=row.created_at,
                status=IncidentStatus(row.status),
                severity=row.severity,
                title=row.title,
                anomaly_event_id=row.anomaly_event_id,
                anomaly_score_id=row.anomaly_score_id,
                evidence_ids=row.evidence_ids,
                fingerprint=row.fingerprint,
            )
            try:
                updated, change = IncidentService.transition(
                    incident,
                    request.status,
                    changed_at=datetime.now(UTC),
                    actor=request.actor,
                    reason=request.reason,
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            if not await repository.apply_transition(updated, change):
                raise HTTPException(status_code=409, detail="incident changed concurrently")
        return {"incident_id": updated.incident_id, "status": updated.status, "change_id": change.change_id}

    @app.get("/api/v1/pools", response_model=list[PoolDefinition])
    async def pools() -> list[PoolDefinition]:
        return list(configured_pools(settings))

    @app.get("/api/v1/pools/{pool_id}/events", response_model=list[PoolEvent])
    async def pool_events(pool_id: str, limit: int = 500) -> list[PoolEvent]:
        async with app.state.database.sessions() as session:
            return await PoolService(PoolEventRepository(session)).events(pool_id, limit)

    @app.get("/api/v1/pools/{pool_id}/metrics", response_model=PoolMetric)
    async def pool_metrics(pool_id: str) -> PoolMetric:
        pool = next((item for item in configured_pools(settings) if item.pool_id == pool_id), None)
        if pool is None:
            raise HTTPException(status_code=404, detail=f"unknown pool {pool_id}")
        async with app.state.database.sessions() as session:
            try:
                return await PoolService(PoolEventRepository(session)).current(
                    pool, settings.health_window_minutes
                )
            except LookupError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()
