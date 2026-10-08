"""Deterministic chain-head continuity checks."""

from collections import defaultdict
from collections.abc import Sequence

from blockpulse.domain.models import ReorgSignal, RpcObservation


def detect_reorganizations(observations: Sequence[RpcObservation]) -> list[ReorgSignal]:
    """Find rollbacks, hash conflicts, and broken parent links per endpoint."""

    signals: list[ReorgSignal] = []
    by_endpoint: dict[str, list[RpcObservation]] = defaultdict(list)
    for observation in observations:
        if observation.success and observation.latest_block_number is not None:
            by_endpoint[observation.endpoint_name].append(observation)

    for endpoint_observations in by_endpoint.values():
        ordered = sorted(endpoint_observations, key=lambda item: (item.observed_at, item.attempt))
        for previous, current in zip(ordered, ordered[1:], strict=False):
            assert previous.latest_block_number is not None
            assert current.latest_block_number is not None
            reason: str | None = None
            if current.latest_block_number < previous.latest_block_number:
                reason = "block_number_rollback"
            elif (
                current.latest_block_number == previous.latest_block_number
                and previous.latest_block_hash
                and current.latest_block_hash
                and previous.latest_block_hash != current.latest_block_hash
            ):
                reason = "conflicting_block_hash"
            elif (
                current.latest_block_number == previous.latest_block_number + 1
                and previous.latest_block_hash
                and current.latest_parent_hash
                and previous.latest_block_hash != current.latest_parent_hash
            ):
                reason = "parent_hash_mismatch"
            if reason is not None:
                signals.append(
                    ReorgSignal(
                        endpoint_name=current.endpoint_name,
                        chain_id=current.chain_id,
                        detected_at=current.observed_at,
                        block_number=current.latest_block_number,
                        previous_block_number=previous.latest_block_number,
                        previous_block_hash=previous.latest_block_hash,
                        observed_block_hash=current.latest_block_hash,
                        reason=reason,
                    )
                )
    return signals
