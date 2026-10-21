"""EWMA and change-point anomaly detectors."""

from collections.abc import Sequence
from math import sqrt

from blockpulse.domain.models import AnomalyScore, FeatureSnapshot, HealthStatus
from blockpulse.shared.identity import feature_reference

def ewma(values: Sequence[float], alpha: float = 0.2) -> list[float]:
    """Return the exponentially weighted moving average series."""

    if not values:
        return []
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def change_point_score(history: Sequence[float], value: float, alpha: float = 0.2) -> float:
    """Measure deviation from the EWMA baseline in standard-deviation units."""

    if len(history) < 2:
        raise ValueError("at least two history values are required")
    baseline = ewma(history, alpha)[-1]
    mean = sum(history) / len(history)
    variance = sum((item - mean) ** 2 for item in history) / len(history)
    standard_deviation = sqrt(variance)
    if standard_deviation == 0:
        return 0.0 if value == baseline else float("inf")
    return abs(value - baseline) / standard_deviation


def detect_change_point_anomalies(
    current: Sequence[FeatureSnapshot],
    history: Sequence[FeatureSnapshot],
    threshold: float = 3.0,
    alpha: float = 0.2,
) -> list[AnomalyScore]:
    """Return traceable anomalies for abrupt EWMA regime changes."""

    if threshold <= 0:
        raise ValueError("threshold must be positive")
    by_feature: dict[tuple[str, str], list[float]] = {}
    for feature in history:
        by_feature.setdefault((feature.entity_id, feature.feature_name), []).append(feature.value)
    results: list[AnomalyScore] = []
    for feature in current:
        values = by_feature.get((feature.entity_id, feature.feature_name), [])
        if len(values) < 3:
            continue
        score_units = change_point_score(values, feature.value, alpha)
        if score_units < threshold:
            continue
        score = 1.0 if score_units == float("inf") else min(1.0, score_units / 10)
        results.append(
            AnomalyScore(
                anomaly_id=feature_reference(
                    "ewma_change_point",
                    "ewma-v1",
                    feature.feature_id,
                    feature.measured_at.isoformat(),
                    0,
                ),
                detector_name="ewma_change_point",
                detector_version="ewma-v1",
                entity_type=feature.entity_type,
                entity_id=feature.entity_id,
                chain_id=feature.chain_id,
                detected_at=feature.measured_at,
                score=score,
                severity=HealthStatus.CRITICAL if score >= 0.8 else HealthStatus.WARNING,
                drivers=[feature.feature_name],
                feature_ids=[feature.feature_id],
                quality_status=feature.quality_status,
            )
        )
    return results
