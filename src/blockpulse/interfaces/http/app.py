"""FastAPI surface for Phase 1 health data."""

from fastapi import FastAPI, HTTPException

from blockpulse.chain_health.application.service import HealthService
from blockpulse.domain.models import HealthMetric, HealthOverview, PoolDefinition, PoolEvent, PoolMetric
from blockpulse.infrastructure.config.chains import configured_chains
from blockpulse.infrastructure.config.pools import configured_pools
from blockpulse.infrastructure.config.settings import get_settings
from blockpulse.infrastructure.database.repositories import Database, ObservationRepository, PoolEventRepository
from blockpulse.liquidity.application.service import PoolService


def create_app(database: Database | None = None) -> FastAPI:
    """Create the API application with an injectable database dependency."""

    settings = get_settings()
    app = FastAPI(title="BlockPulse API", version="0.1.0")
    app.state.database = database or Database(settings.database_url)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

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
