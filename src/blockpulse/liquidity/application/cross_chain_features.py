"""Cross-chain feature generation for comparable pool prices."""

from collections import defaultdict
from collections.abc import Mapping, Sequence

from blockpulse.domain.models import FeatureSnapshot
from blockpulse.shared.identity import feature_reference


def build_cross_chain_price_features(
    pool_price_features: Sequence[FeatureSnapshot],
    asset_pair_by_pool: Mapping[str, str],
    feature_version: str = "cross-chain-v1",
) -> list[FeatureSnapshot]:
    """Measure cross-chain price dispersion for the same asset pair and window."""

    grouped: dict[tuple[str, str], list[FeatureSnapshot]] = defaultdict(list)
    for feature in pool_price_features:
        if feature.feature_name != "pool_price_token1_per_token0":
            continue
        pair = asset_pair_by_pool.get(feature.entity_id)
        if pair is not None:
            grouped[(pair, feature.measured_at.isoformat())].append(feature)

    result: list[FeatureSnapshot] = []
    for (pair, measured_at), values in sorted(grouped.items()):
        if len(values) < 2:
            continue
        prices = [value.value for value in values]
        mean_price = sum(prices) / len(prices)
        dispersion = (max(prices) - min(prices)) / mean_price if mean_price else 0.0
        sources = [source for value in values for source in value.source_observation_ids]
        for name, value in {
            "cross_chain_price_mean": mean_price,
            "cross_chain_price_dispersion_pct": dispersion * 100,
        }.items():
            result.append(
                FeatureSnapshot(
                    feature_id=feature_reference(
                        name, feature_version, pair, measured_at, values[0].window_minutes
                    ),
                    feature_name=name,
                    feature_version=feature_version,
                    entity_type="asset_pair",
                    entity_id=pair,
                    chain_id=0,
                    measured_at=values[0].measured_at,
                    window_minutes=values[0].window_minutes,
                    value=value,
                    source_observation_ids=sources,
                )
            )
    return result
