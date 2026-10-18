"""Seeded multivariate Isolation Forest detector."""

from collections.abc import Sequence
from math import exp

from sklearn.ensemble import IsolationForest

from blockpulse.domain.models import AnomalyScore, FeatureVector, HealthStatus
from blockpulse.shared.identity import feature_reference


class IsolationForestDetector:
    """Fit and score aligned feature vectors with a reproducible model."""

    name = "isolation_forest"
    version = "iforest-v1"

    def __init__(
        self,
        feature_names: Sequence[str],
        contamination: float = "auto",
        random_state: int = 42,
        n_estimators: int = 100,
    ) -> None:
        if not feature_names:
            raise ValueError("at least one feature name is required")
        self.feature_names = tuple(feature_names)
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=n_estimators,
        )
        self._fitted = False

    def fit(self, vectors: Sequence[FeatureVector]) -> None:
        """Fit only on quality-approved training vectors."""

        approved = [vector for vector in vectors if vector.quality_status == "valid"]
        if len(approved) < 2:
            raise ValueError("at least two valid vectors are required")
        self.model.fit(self._matrix(approved))
        self._fitted = True

    def detect(self, vectors: Sequence[FeatureVector]) -> list[AnomalyScore]:
        """Return anomaly scores with the contributing feature IDs attached."""

        if not self._fitted:
            raise RuntimeError("detector must be fitted before detection")
        if not vectors:
            return []
        values = self.model.decision_function(self._matrix(vectors))
        predictions = self.model.predict(self._matrix(vectors))
        results: list[AnomalyScore] = []
        for vector, decision, prediction in zip(vectors, values, predictions, strict=True):
            score = min(1.0, max(0.0, 1 / (1 + exp(float(decision) * 5))))
            if prediction != -1:
                continue
            results.append(
                AnomalyScore(
                    anomaly_id=feature_reference(
                        self.name, self.version, vector.vector_id, vector.measured_at.isoformat(), 0
                    ),
                    detector_name=self.name,
                    detector_version=self.version,
                    entity_type=vector.entity_type,
                    entity_id=vector.entity_id,
                    chain_id=vector.chain_id,
                    detected_at=vector.measured_at,
                    score=score,
                    severity=HealthStatus.CRITICAL if score >= 0.8 else HealthStatus.WARNING,
                    drivers=list(self.feature_names),
                    feature_ids=list(vector.feature_ids.values()),
                    quality_status=vector.quality_status,
                )
            )
        return results

    def _matrix(self, vectors: Sequence[FeatureVector]) -> list[list[float]]:
        return [[vector.feature_values[name] for name in self.feature_names] for vector in vectors]
