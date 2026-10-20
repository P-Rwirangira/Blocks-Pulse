"""Build persisted evaluation records from detector test results."""

from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256

from blockpulse.chain_health.application.evaluation import EvaluationReport
from blockpulse.domain.models import ModelEvaluation


def build_model_evaluation(
    detector_name: str,
    detector_version: str,
    feature_version: str,
    evaluated_at: datetime,
    train_count: int,
    validation_count: int,
    test_count: int,
    report: EvaluationReport,
    parameters: Mapping[str, object],
) -> ModelEvaluation:
    """Create an immutable evaluation record with a deterministic run ID."""

    identity = "|".join(
        [detector_name, detector_version, feature_version, evaluated_at.isoformat()]
    )
    run_id = sha256(identity.encode("utf-8")).hexdigest()
    return ModelEvaluation(
        run_id=run_id,
        detector_name=detector_name,
        detector_version=detector_version,
        feature_version=feature_version,
        evaluated_at=evaluated_at,
        train_count=train_count,
        validation_count=validation_count,
        test_count=test_count,
        precision=report.precision,
        recall=report.recall,
        false_positive_rate=report.false_positive_rate,
        parameters=dict(parameters),
    )
