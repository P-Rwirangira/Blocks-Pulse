"""Explainable robust statistical anomaly baseline."""

from collections.abc import Sequence
from statistics import median

from blockpulse.domain.models import AnomalyScore, FeatureSnapshot, HealthStatus
from blockpulse.shared.identity import feature_reference


BASELINE_VERSION = "mad-v1"


def robust_z_score(value: float, history: Sequence[float]) -> float:
    """Calculate a median/MAD z-score without assuming normality."""

    if not history:
        raise ValueError("history is required")
    center = median(history)
    deviations = [abs(item - center) for item in history]
    mad = median(deviations)
    if mad == 0:
        return 0.0 if value == center else float("inf")
    return abs(value - center) / (1.4826 * mad)


def detect_robust_anomalies(
    current: Sequence[FeatureSnapshot],
    history: Sequence[FeatureSnapshot],
    threshold: float = 3.5,
) -> list[AnomalyScore]:
    """Score current features against same-name historical feature values."""

    if threshold <= 0:
        raise ValueError("threshold must be positive")
    historical: dict[tuple[str, str], list[float]] = {}
    for feature in history:
        historical.setdefault((feature.entity_id, feature.feature_name), []).append(feature.value)

    results: list[AnomalyScore] = []
    for feature in current:
        values = historical.get((feature.entity_id, feature.feature_name), [])
        if len(values) < 3:
            continue
        z_score = robust_z_score(feature.value, values)
        if z_score < threshold:
            continue
        score = 1.0 if z_score == float("inf") else min(1.0, z_score / 10)
        severity = HealthStatus.CRITICAL if score >= 0.8 else HealthStatus.WARNING
        anomaly_id = feature_reference(
            "robust_anomaly", BASELINE_VERSION, feature.feature_id, feature.measured_at.isoformat(), 0
        )
        results.append(
            AnomalyScore(
                anomaly_id=anomaly_id,
                detector_name="robust_mad",
                detector_version=BASELINE_VERSION,
                entity_type=feature.entity_type,
                entity_id=feature.entity_id,
                chain_id=feature.chain_id,
                detected_at=feature.measured_at,
                score=score,
                severity=severity,
                drivers=[feature.feature_name],
                feature_ids=[feature.feature_id],
                quality_status=feature.quality_status,
            )
        )
    return results
