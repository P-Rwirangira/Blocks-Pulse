"""FastAPI surface for Phase 1 health data."""

from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from blockpulse.domain.models import (
    Incident,
    IncidentStatus,
    BinanceKline,
)
from blockpulse.infrastructure.config.settings import get_settings
from blockpulse.infrastructure.database.repositories import (
    Database,
    IncidentRepository,
    BinanceKlineRepository,
)
from blockpulse.incidents.application.service import IncidentService
from blockpulse.infrastructure.observability import MetricsRegistry


class IncidentTransitionRequest(BaseModel):
    """Explicit operator intent for one lifecycle change."""

    status: IncidentStatus
    actor: str = Field(min_length=1, max_length=120)
    reason: str | None = Field(default=None, max_length=500)


def create_app(
    database: Database | None = None,
    metrics: MetricsRegistry | None = None,
) -> FastAPI:
    """Create the API application with an injectable database dependency."""

    settings = get_settings()
    app = FastAPI(title="BlockPulse API", version="0.1.0")
    app.state.database = database or Database(settings.database_url)
    app.state.metrics = metrics or MetricsRegistry()

    @app.middleware("http")
    async def collect_http_metrics(request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        started = datetime.now(UTC)
        response = await call_next(request)
        route = getattr(request.scope.get("route"), "path", request.url.path)
        duration = (datetime.now(UTC) - started).total_seconds()
        app.state.metrics.observe_http(request.method, route, response.status_code, duration)
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=app.state.metrics.render(), media_type="text/plain; version=0.0.4")

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        """Confirm that the API can reach its configured database."""

        try:
            async with app.state.database.sessions() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="database is not ready") from exc
        return {"status": "ready"}

    @app.get("/api/v1/incidents")
    async def incidents(
        chain_id: int | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, object]]:
        """List operator incidents through a bounded read-only projection."""

        async with app.state.database.sessions() as session:
            rows = await IncidentRepository(session).recent(chain_id=chain_id, limit=limit)
        active = [row for row in rows if row.status not in {"resolved", "suppressed"}]
        counts: dict[str, int] = {}
        for row in active:
            counts[row.severity] = counts.get(row.severity, 0) + 1
        app.state.metrics.set_active_incidents(counts)
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

    @app.get("/api/v1/markets/{symbol}/klines", response_model=list[BinanceKline])
    async def market_klines(symbol: str, interval: str = "1h", limit: int = Query(500, ge=1, le=1_000)) -> list[BinanceKline]:
        normalized_symbol = symbol.upper()
        async with app.state.database.sessions() as session:
            rows = await BinanceKlineRepository(session).recent(normalized_symbol, interval, limit)
        return [
            BinanceKline(
                symbol=row.symbol,
                interval=row.interval,
                open_time=row.open_time,
                close_time=row.close_time,
                open_price=row.open_price,
                high_price=row.high_price,
                low_price=row.low_price,
                close_price=row.close_price,
                volume=row.volume,
                quote_volume=row.quote_volume,
                trade_count=row.trade_count,
                taker_buy_volume=row.taker_buy_volume,
                taker_buy_quote_volume=row.taker_buy_quote_volume,
                collected_at=row.collected_at,
                source=row.source,
                raw_payload=row.raw_payload,
            )
            for row in rows
        ]

    return app


app = create_app()
