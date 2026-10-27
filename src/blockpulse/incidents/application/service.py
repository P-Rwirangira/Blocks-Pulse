"""Deterministic incident creation and lifecycle rules."""

from datetime import datetime
from hashlib import sha256
from typing import Final

from blockpulse.domain.models import (
    AnomalyEvent,
    AnomalyScore,
    Incident,
    IncidentStatus,
    IncidentStatusChange,
)


ALLOWED_TRANSITIONS: Final[dict[IncidentStatus, frozenset[IncidentStatus]]] = {
    IncidentStatus.OPEN: frozenset({IncidentStatus.INVESTIGATING, IncidentStatus.SUPPRESSED}),
    IncidentStatus.INVESTIGATING: frozenset(
        {IncidentStatus.ACKNOWLEDGED, IncidentStatus.RESOLVED, IncidentStatus.SUPPRESSED}
    ),
    IncidentStatus.ACKNOWLEDGED: frozenset(
        {IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED, IncidentStatus.SUPPRESSED}
    ),
    IncidentStatus.RESOLVED: frozenset(),
    IncidentStatus.SUPPRESSED: frozenset({IncidentStatus.OPEN}),
}


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

    def open_from_score(self, anomaly: AnomalyScore, *, dedupe_window_minutes: int = 15) -> Incident:
        """Create the same incident for a persisted detector result every time."""

        fingerprint = self.fingerprint(anomaly, dedupe_window_minutes=dedupe_window_minutes)
        incident_id = f"inc-{fingerprint[:20]}"
        return Incident(
            incident_id=incident_id,
            chain_id=anomaly.chain_id,
            created_at=anomaly.detected_at,
            status=IncidentStatus.OPEN,
            severity=anomaly.severity,
            title=f"{anomaly.entity_type} anomaly on {anomaly.entity_id}",
            anomaly_event_id=anomaly.anomaly_id,
            anomaly_score_id=anomaly.anomaly_id,
            evidence_ids=[*anomaly.feature_ids],
            fingerprint=fingerprint,
        )

    @staticmethod
    def fingerprint(anomaly: AnomalyScore, *, dedupe_window_minutes: int = 15) -> str:
        """Build a stable grouping key for one explicit time window."""

        if dedupe_window_minutes <= 0:
            raise ValueError("dedupe_window_minutes must be positive")
        timestamp_seconds = int(anomaly.detected_at.timestamp())
        bucket = timestamp_seconds // (dedupe_window_minutes * 60)

        value = "|".join(
            (
                str(anomaly.chain_id),
                anomaly.entity_type,
                anomaly.entity_id,
                anomaly.severity.value,
                ",".join(sorted(anomaly.drivers)),
                str(dedupe_window_minutes),
                str(bucket),
            )
        )
        return sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def transition(
        incident: Incident,
        to_status: IncidentStatus,
        *,
        changed_at: datetime,
        actor: str,
        reason: str | None = None,
    ) -> tuple[Incident, IncidentStatusChange]:
        """Apply one explicit lifecycle transition and return its audit event."""

        if to_status not in ALLOWED_TRANSITIONS[incident.status]:
            raise ValueError(f"Invalid incident transition: {incident.status} -> {to_status}")
        change_id = sha256(
            f"{incident.incident_id}|{incident.status}|{to_status}|{changed_at.isoformat()}".encode()
        ).hexdigest()[:24]
        updated = incident.model_copy(update={"status": to_status})
        change = IncidentStatusChange(
            change_id=change_id,
            incident_id=incident.incident_id,
            from_status=incident.status,
            to_status=to_status,
            changed_at=changed_at,
            actor=actor,
            reason=reason,
        )
        return updated, change
