from datetime import UTC, datetime

import pytest

from blockpulse.domain import FeatureSnapshot


def test_feature_snapshot_requires_traceable_source() -> None:
    with pytest.raises(ValueError):
        FeatureSnapshot(
            feature_id="x",
            feature_name="rpc_error_rate",
            feature_version="v1",
            entity_type="chain",
            entity_id="8453",
            chain_id=8453,
            measured_at=datetime.now(UTC),
            window_minutes=15,
            value=0.1,
            source_observation_ids=[],
        )
