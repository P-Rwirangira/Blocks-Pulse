"""Incident creation and lifecycle rules."""

from hashlib import sha256

from blockpulse.domain.models import AnomalyEvent, Incident, IncidentStatus


class IncidentService:
    """Create deterministic incidents from anomaly events."""

    def open_from_anomaly(self, anomaly: AnomalyEvent) -> Incident:
        """Create an open incident with evidence references."""

        incident_id = sha256(anomaly.event_id.encode("utf-8")).hexdigest()[:20]
        evidence_ids = [anomaly.event_id]
        return Incident(
            incident_id=f"inc-{incident_id}",
            chain_id=anomaly.chain_id,
            created_at=anomaly.detected_at,
            status=IncidentStatus.OPEN,
            severity=anomaly.status,
            title=f"RPC health anomaly on chain {anomaly.chain_id}",
            anomaly_event_id=anomaly.event_id,
            evidence_ids=evidence_ids,
        )
