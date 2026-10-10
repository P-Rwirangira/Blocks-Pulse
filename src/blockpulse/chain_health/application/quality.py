"""Data-quality checks for chain-health observations."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from blockpulse.domain.models import RpcObservation


@dataclass(frozen=True, slots=True)
class ObservationQualityReport:
    """Evidence-backed quality result for one observation window."""

    checked_at: datetime
    observation_count: int
    stale: bool
    duplicate_count: int
    gap_count: int
    issues: tuple[str, ...]

    @property
    def valid(self) -> bool:
        """Return whether observations are suitable for downstream metrics."""

        return not self.issues


def assess_observation_quality(
    observations: Sequence[RpcObservation],
    checked_at: datetime,
    expected_interval: timedelta,
) -> ObservationQualityReport:
    """Check freshness, duplicate identities, timezones, and collection gaps."""

    if expected_interval <= timedelta(0):
        raise ValueError("expected interval must be positive")
    if checked_at.tzinfo is None:
        raise ValueError("checked_at must be timezone-aware")
    checked_at = checked_at.astimezone(UTC)
    issues: list[str] = []
    if not observations:
        issues.append("no_observations")

    duplicate_count = len(observations) - len(
        {
            (item.endpoint_name, item.chain_id, item.observed_at, item.attempt)
            for item in observations
        }
    )
    if duplicate_count:
        issues.append("duplicate_observations")

    if any(item.observed_at.tzinfo is None for item in observations):
        issues.append("naive_observation_timestamp")

    latest = max((item.observed_at for item in observations), default=checked_at)
    stale = checked_at - latest.astimezone(UTC) > expected_interval * 2
    if stale:
        issues.append("stale_observations")

    by_endpoint: dict[str, list[RpcObservation]] = defaultdict(list)
    for observation in observations:
        by_endpoint[observation.endpoint_name].append(observation)
    gap_count = 0
    for endpoint_observations in by_endpoint.values():
        ordered = sorted(endpoint_observations, key=lambda item: item.observed_at)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if current.observed_at - previous.observed_at > expected_interval * 2:
                gap_count += 1
    if gap_count:
        issues.append("observation_gaps")

    return ObservationQualityReport(
        checked_at=checked_at,
        observation_count=len(observations),
        stale=stale,
        duplicate_count=duplicate_count,
        gap_count=gap_count,
        issues=tuple(issues),
    )
