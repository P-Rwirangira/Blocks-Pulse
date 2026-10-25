"""Validation controls for evidence-grounded AI investigation responses."""

from math import isclose

from blockpulse.domain.models import AIInvestigationResponse, EvidencePackage


class AIResponseValidator:
    """Reject unsupported citations and numerical claims before presentation."""

    def validate(
        self,
        response: AIInvestigationResponse,
        package: EvidencePackage,
        *,
        numeric_tolerance: float = 1e-6,
    ) -> AIInvestigationResponse:
        if response.incident_id != package.incident_id:
            raise ValueError("AI response incident does not match evidence package")
        evidence_by_id = {item.evidence_id: item for item in package.evidence}
        for claim in response.claims:
            if any(evidence_id not in evidence_by_id for evidence_id in claim.evidence_ids):
                raise ValueError("AI claim cites evidence outside the package")
            if claim.numeric_value is not None and not self._numeric_value_is_grounded(
                claim.numeric_value, claim.evidence_ids, evidence_by_id, numeric_tolerance
            ):
                raise ValueError("AI numeric claim does not match cited evidence")
        if package.quality_warnings and not response.unknowns:
            raise ValueError("AI response must disclose package quality warnings")
        return response.model_copy(update={"grounded": True})

    @staticmethod
    def _numeric_value_is_grounded(value: float, evidence_ids: list[str], evidence_by_id: dict, tolerance: float) -> bool:
        for evidence_id in evidence_ids:
            payload = evidence_by_id[evidence_id].payload
            candidate = payload.get("value")
            if isinstance(candidate, (int, float)) and isclose(value, float(candidate), abs_tol=tolerance):
                return True
            candidate = payload.get("score")
            if isinstance(candidate, (int, float)) and isclose(value, float(candidate), abs_tol=tolerance):
                return True
        return False
