"""Evidence package assembly for incident investigations."""

from datetime import datetime
from hashlib import sha256
from typing import Sequence

from blockpulse.domain.models import (
    AnomalyScore,
    EvidencePackage,
    FeatureSnapshot,
    Incident,
    IncidentEvidence,
    RpcObservation,
)


class EvidencePackageBuilder:
    """Build a deterministic, bounded investigation input from stored facts."""

    def build(
        self,
        incident: Incident,
        anomaly: AnomalyScore,
        features: Sequence[FeatureSnapshot],
        *,
        generated_at: datetime,
        observations: Sequence[RpcObservation] = (),
        quality_warnings: Sequence[str] = (),
    ) -> EvidencePackage:
        evidence = [
            IncidentEvidence(
                evidence_id=self._evidence_id(incident.incident_id, "anomaly", anomaly.anomaly_id),
                incident_id=incident.incident_id,
                evidence_type="anomaly_score",
                source_id=anomaly.anomaly_id,
                observed_at=anomaly.detected_at,
                summary=(f"{anomaly.detector_name} scored {anomaly.score:.3f} with drivers: "
                         f"{', '.join(anomaly.drivers)}"),
                payload=anomaly.model_dump(mode="json"),
            )
        ]
        warnings: list[str] = list(quality_warnings)
        for feature in sorted(features, key=lambda item: (item.measured_at, item.feature_id)):
            if feature.quality_status != "valid":
                warnings.append(f"Feature {feature.feature_id} is {feature.quality_status}.")
            evidence.append(
                IncidentEvidence(
                    evidence_id=self._evidence_id(incident.incident_id, "feature", feature.feature_id),
                    incident_id=incident.incident_id,
                    evidence_type="feature_snapshot",
                    source_id=feature.feature_id,
                    observed_at=feature.measured_at,
                    summary=f"{feature.feature_name}={feature.value}",
                    payload=feature.model_dump(mode="json"),
                )
            )
        if not features:
            warnings.append("No feature snapshots were available for this incident.")
        for observation in sorted(observations, key=lambda item: (item.observed_at, item.endpoint_name)):
            source_id = self._observation_id(observation)
            evidence.append(
                IncidentEvidence(
                    evidence_id=self._evidence_id(incident.incident_id, "observation", source_id),
                    incident_id=incident.incident_id,
                    evidence_type="rpc_observation",
                    source_id=source_id,
                    observed_at=observation.observed_at,
                    summary=(f"{observation.endpoint_name} {'succeeded' if observation.success else 'failed'} "
                             f"in {observation.latency_ms}ms"),
                    payload=observation.model_dump(mode="json"),
                )
            )
        return EvidencePackage(
            package_id=self._package_id(incident.incident_id, evidence),
            incident_id=incident.incident_id,
            generated_at=generated_at,
            evidence=evidence,
            detector_name=anomaly.detector_name,
            detector_version=anomaly.detector_version,
            anomaly_score=anomaly.score,
            quality_warnings=warnings,
            unknowns=["Root cause is not established by an anomaly score alone."],
        )

    @staticmethod
    def _evidence_id(incident_id: str, kind: str, source_id: str) -> str:
        return "ev-" + sha256(f"{incident_id}|{kind}|{source_id}".encode()).hexdigest()[:24]

    @staticmethod
    def _package_id(incident_id: str, evidence: Sequence[IncidentEvidence]) -> str:
        source_ids = ",".join(item.source_id for item in evidence)
        return "pkg-" + sha256(f"{incident_id}|{source_ids}".encode()).hexdigest()[:24]

    @staticmethod
    def _observation_id(observation: RpcObservation) -> str:
        value = "|".join(
            (
                observation.endpoint_name,
                str(observation.chain_id),
                observation.observed_at.isoformat(),
                str(observation.attempt),
            )
        )
        return sha256(value.encode()).hexdigest()
