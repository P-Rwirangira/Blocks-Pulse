"""FastAPI surface for Phase 1 health data."""

from fastapi import FastAPI, HTTPException

from blockpulse.config import get_settings
from blockpulse.domain import HealthMetric
from blockpulse.health_service import HealthService
from blockpulse.storage import Database, ObservationRepository


def create_app(database: Database | None = None) -> FastAPI:
    """Create the API application with an injectable database dependency."""

    settings = get_settings()
    app = FastAPI(title="BlockPulse API", version="0.1.0")
    app.state.database = database or Database(settings.database_url)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/chains/{chain_id}/health", response_model=HealthMetric)
    async def chain_health(chain_id: int) -> HealthMetric:
        async with app.state.database.sessions() as session:
            service = HealthService(ObservationRepository(session))
            try:
                return await service.current(chain_id, settings.health_window_minutes)
            except LookupError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()

