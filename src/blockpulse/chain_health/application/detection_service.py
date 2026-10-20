"""Application orchestration for fitting, scoring, and persisting anomalies."""

from collections.abc import Sequence
from typing import Protocol

from blockpulse.domain.models import AnomalyScore, FeatureVector


class Detector(Protocol):
    """Minimal detector port used by the application service."""

    def fit(self, vectors: Sequence[FeatureVector]) -> None:
        """Fit on historical training vectors."""

    def detect(self, vectors: Sequence[FeatureVector]) -> list[AnomalyScore]:
        """Score current vectors."""


class AnomalyDetectionService:
    """Coordinate detector execution and idempotent anomaly persistence."""

    def __init__(self, detector: Detector, repository: object) -> None:
        self.detector = detector
        self.repository = repository

    async def run(
        self,
        training: Sequence[FeatureVector],
        current: Sequence[FeatureVector],
    ) -> tuple[list[AnomalyScore], int]:
        """Fit on historical vectors, score current vectors, and persist results."""

        self.detector.fit(training)
        anomalies = self.detector.detect(current)
        inserted = await self.repository.add_many(anomalies)
        return anomalies, inserted
