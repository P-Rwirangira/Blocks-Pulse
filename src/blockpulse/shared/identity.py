"""Stable identity helpers shared by persistence and feature layers."""

from hashlib import sha256

from blockpulse.domain.models import RpcObservation


def observation_reference(observation: RpcObservation) -> str:
    """Return the stable identity of one captured observation."""

    value = "|".join(
        [
            observation.endpoint_name,
            str(observation.chain_id),
            observation.observed_at.isoformat(),
            str(observation.attempt),
        ]
    )
    return sha256(value.encode("utf-8")).hexdigest()


def feature_reference(
    feature_name: str,
    feature_version: str,
    entity_id: str,
    measured_at: str,
    window_minutes: int,
) -> str:
    """Return a stable identity for one feature snapshot."""

    value = "|".join(
        [feature_name, feature_version, entity_id, measured_at, str(window_minutes)]
    )
    return sha256(value.encode("utf-8")).hexdigest()
