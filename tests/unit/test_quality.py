from datetime import UTC, datetime, timedelta

import pytest

from blockpulse.chain_health.application.quality import assess_observation_quality
from blockpulse.domain import RpcObservation


def make_observation(at: datetime, attempt: int = 0) -> RpcObservation:
    return RpcObservation(
        endpoint_name="base-a",
        chain_id=8453,
        observed_at=at,
        attempt=attempt,
        latency_ms=100,
        success=True,
        latest_block_number=100,
    )


def test_quality_report_detects_staleness_and_gaps() -> None:
    first = make_observation(datetime(2026, 10, 10, 9, 0, tzinfo=UTC))
    second = make_observation(datetime(2026, 10, 10, 9, 10, tzinfo=UTC))

    report = assess_observation_quality(
        [first, second],
        checked_at=datetime(2026, 10, 10, 9, 20, tzinfo=UTC),
        expected_interval=timedelta(minutes=2),
    )

    assert report.valid is False
    assert report.stale is True
    assert report.gap_count == 1
    assert set(report.issues) == {"stale_observations", "observation_gaps"}


def test_quality_report_counts_retry_duplicates_only_by_identity() -> None:
    observed_at = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
    report = assess_observation_quality(
        [make_observation(observed_at), make_observation(observed_at, attempt=1)],
        checked_at=observed_at + timedelta(seconds=30),
        expected_interval=timedelta(minutes=1),
    )

    assert report.valid is True
    assert report.duplicate_count == 0


def test_quality_requires_positive_interval_and_aware_check_time() -> None:
    observation = make_observation(datetime(2026, 10, 10, 9, 0, tzinfo=UTC))
    with pytest.raises(ValueError, match="interval"):
        assess_observation_quality([observation], observation.observed_at, timedelta(0))
    with pytest.raises(ValueError, match="timezone"):
        assess_observation_quality([observation], datetime(2026, 10, 10, 9, 0), timedelta(minutes=1))
