"""Deterministic regression cases for the grounded AI safety boundary."""

from collections.abc import Sequence

from pydantic import BaseModel, Field

from blockpulse.domain.models import AIInvestigationResponse, EvidencePackage

from .ai_validation import AIResponseValidator


class AIValidationCase(BaseModel):
    """One expected accept/reject case for validator regression testing."""

    name: str
    response: AIInvestigationResponse
    expected_valid: bool


class AIValidationResult(BaseModel):
    """Stable evaluation summary suitable for CI and run metadata."""

    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed_cases: list[str] = Field(default_factory=list)


class AIValidationEvaluator:
    """Run safety cases without invoking an LLM or mutating application state."""

    def __init__(self, validator: AIResponseValidator | None = None) -> None:
        self.validator = validator or AIResponseValidator()

    def evaluate(
        self,
        package: EvidencePackage,
        cases: Sequence[AIValidationCase],
    ) -> AIValidationResult:
        failed: list[str] = []
        for case in cases:
            valid = True
            try:
                self.validator.validate(case.response, package)
            except ValueError:
                valid = False
            if valid != case.expected_valid:
                failed.append(case.name)
        return AIValidationResult(total=len(cases), passed=len(cases) - len(failed), failed_cases=failed)
