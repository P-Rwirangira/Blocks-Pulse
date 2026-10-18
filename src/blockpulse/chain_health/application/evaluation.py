"""Time-aware anomaly evaluation utilities."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from blockpulse.domain.models import FeatureSnapshot


@dataclass(frozen=True, slots=True)
class TimeSplit:
    """Chronological train, validation, and test partitions."""

    train: tuple[FeatureSnapshot, ...]
    validation: tuple[FeatureSnapshot, ...]
    test: tuple[FeatureSnapshot, ...]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Basic classification and alert-volume metrics."""

    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    false_positive_rate: float


def chronological_split(
    features: Sequence[FeatureSnapshot],
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> TimeSplit:
    """Split by timestamp without allowing future observations into training."""

    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("split fractions must be in (0, 1)")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train and validation fractions must leave a test set")
    ordered = tuple(sorted(features, key=lambda item: item.measured_at))
    if len(ordered) < 3:
        raise ValueError("at least three features are required")
    train_end = max(1, int(len(ordered) * train_fraction))
    validation_end = max(train_end + 1, int(len(ordered) * (train_fraction + validation_fraction)))
    validation_end = min(validation_end, len(ordered) - 1)
    return TimeSplit(ordered[:train_end], ordered[train_end:validation_end], ordered[validation_end:])


def evaluate_binary_scores(
    scores: Sequence[float], labels: Sequence[bool], threshold: float
) -> EvaluationReport:
    """Evaluate scores against fixed labels without random resampling."""

    if len(scores) != len(labels) or not scores:
        raise ValueError("scores and labels must be equally sized and non-empty")
    predicted = [score >= threshold for score in scores]
    tp = sum(prediction and label for prediction, label in zip(predicted, labels, strict=True))
    fp = sum(prediction and not label for prediction, label in zip(predicted, labels, strict=True))
    tn = sum(not prediction and not label for prediction, label in zip(predicted, labels, strict=True))
    fn = sum(not prediction and label for prediction, label in zip(predicted, labels, strict=True))
    return EvaluationReport(
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        precision=tp / (tp + fp) if tp + fp else 0.0,
        recall=tp / (tp + fn) if tp + fn else 0.0,
        false_positive_rate=fp / (fp + tn) if fp + tn else 0.0,
    )
