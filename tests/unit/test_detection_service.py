import asyncio
from datetime import UTC, datetime

from blockpulse.chain_health.application.detection_service import AnomalyDetectionService
from blockpulse.domain import AnomalyScore, FeatureVector, HealthStatus


class FakeDetector:
    def __init__(self) -> None:
        self.fitted = False

    def fit(self, vectors: list[FeatureVector]) -> None:
        self.fitted = bool(vectors)

    def detect(self, vectors: list[FeatureVector]) -> list[AnomalyScore]:
        assert self.fitted
        return [
            AnomalyScore(
                anomaly_id="a1",
                detector_name="fake",
                detector_version="test-v1",
                entity_type="chain",
                entity_id="8453",
                chain_id=8453,
                detected_at=datetime(2026, 10, 20, 9, 0, tzinfo=UTC),
                score=0.9,
                severity=HealthStatus.CRITICAL,
                drivers=["test"],
                feature_ids=["feature-1"],
            )
        ]


class FakeRepository:
    async def add_many(self, anomalies: list[AnomalyScore]) -> int:
        return len(anomalies)


class MetricsSpy:
    def __init__(self) -> None:
        self.values: list[tuple[str, str]] = []

    def observe_anomaly(self, detector: str, severity: str) -> None:
        self.values.append((detector, severity))


def test_detection_service_fits_scores_and_persists() -> None:
    vector = FeatureVector(
        vector_id="v1",
        entity_type="chain",
        entity_id="8453",
        chain_id=8453,
        measured_at=datetime(2026, 10, 20, 9, 0, tzinfo=UTC),
        feature_values={"error_rate": 0.1},
        feature_ids={"error_rate": "feature-1"},
    )

    async def scenario() -> None:
        metrics = MetricsSpy()
        anomalies, inserted = await AnomalyDetectionService(
            FakeDetector(), FakeRepository(), metrics=metrics
        ).run([vector], [vector])
        assert len(anomalies) == inserted == 1
        assert metrics.values == [("fake", "critical")]

    asyncio.run(scenario())
