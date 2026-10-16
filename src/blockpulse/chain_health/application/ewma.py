"""EWMA and change-point anomaly detectors."""

from collections.abc import Sequence
from math import sqrt


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
