"""Align flat feature snapshots into model-ready vectors."""

from collections import defaultdict
from collections.abc import Sequence

from blockpulse.domain.models import FeatureSnapshot, FeatureVector


def build_feature_vectors(
    features: Sequence[FeatureSnapshot], required_features: Sequence[str]
) -> list[FeatureVector]:
    """Build complete vectors and discard incomplete windows explicitly."""

    required = tuple(dict.fromkeys(required_features))
    if not required:
        raise ValueError("at least one required feature is needed")
    grouped: dict[tuple[str, str, str], list[FeatureSnapshot]] = defaultdict(list)
    for feature in features:
        grouped[(feature.entity_id, feature.measured_at.isoformat(), feature.feature_version)].append(
            feature
        )

    vectors: list[FeatureVector] = []
    for (entity_id, measured_at, _), values in sorted(grouped.items()):
        by_name = {feature.feature_name: feature for feature in values}
        if any(name not in by_name for name in required):
            continue
        selected = [by_name[name] for name in required]
        first = selected[0]
        vectors.append(
            FeatureVector(
                vector_id="|".join([entity_id, measured_at, first.feature_version]),
                entity_type=first.entity_type,
                entity_id=entity_id,
                chain_id=first.chain_id,
                measured_at=first.measured_at,
                feature_values={name: by_name[name].value for name in required},
                feature_ids={name: by_name[name].feature_id for name in required},
                quality_status=(
                    "valid" if all(item.quality_status == "valid" for item in selected) else "invalid"
                ),
            )
        )
    return vectors
