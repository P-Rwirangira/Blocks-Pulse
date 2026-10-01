"""Configuration-driven registry for monitored pools."""

import json

from blockpulse.domain.models import PoolDefinition
from blockpulse.infrastructure.config.settings import Settings


def configured_pools(settings: Settings) -> tuple[PoolDefinition, ...]:
    """Parse the JSON pool registry from settings."""

    if not settings.pools_json.strip():
        return ()
    payload = json.loads(settings.pools_json)
    if not isinstance(payload, list):
        raise ValueError("BLOCKPULSE_POOLS_JSON must be a JSON array")
    return tuple(PoolDefinition.model_validate(item) for item in payload)


def pools_for_chain(
    settings: Settings, chain_id: int
) -> tuple[PoolDefinition, ...]:
    """Return configured pools for one chain."""

    return tuple(pool for pool in configured_pools(settings) if pool.chain_id == chain_id)
