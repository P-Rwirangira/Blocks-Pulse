from datetime import UTC, datetime, timedelta

import pytest

from blockpulse.chain_health.application.evaluation import chronological_split, evaluate_binary_scores
from blockpulse.domain import FeatureSnapshot


def feature(index: int) -> FeatureSnapshot:
    return FeatureSnapshot(
        feature_id=f"feature-{index}",
        feature_name="rpc_error_rate",
        feature_version="rpc-v1",
        entity_type="chain",
        entity_id="8453",
        chain_id=8453,
        measured_at=datetime(2026, 10, 17, 9, 0, tzinfo=UTC) + timedelta(minutes=index),
        window_minutes=15,
        value=float(index),
        source_observation_ids=[f"observation-{index}"],
    )


def test_chronological_split_preserves_time_order() -> None:
    split = chronological_split([feature(index) for index in range(10)])
    assert split.train[-1].measured_at < split.validation[0].measured_at
    assert split.validation[-1].measured_at < split.test[0].measured_at


def test_binary_evaluation_reports_false_positives() -> None:
    report = evaluate_binary_scores([0.1, 0.9, 0.8], [False, True, False], threshold=0.5)
    assert report.true_positives == 1
    assert report.false_positives == 1
    assert report.precision == 0.5


def test_split_requires_enough_features() -> None:
    with pytest.raises(ValueError, match="three"):
        chronological_split([feature(0), feature(1)])
