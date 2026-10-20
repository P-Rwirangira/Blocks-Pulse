from datetime import UTC, datetime

from blockpulse.chain_health.application.evaluation import EvaluationReport
from blockpulse.chain_health.application.evaluation_runner import build_model_evaluation


def test_evaluation_runner_creates_reproducible_model_record() -> None:
    report = EvaluationReport(8, 2, 7, 3, 0.8, 0.73, 0.22)
    evaluated_at = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
    first = build_model_evaluation(
        "robust_mad", "mad-v1", "rpc-v1", evaluated_at, 10, 4, 10, report, {"threshold": 3.5}
    )
    second = build_model_evaluation(
        "robust_mad", "mad-v1", "rpc-v1", evaluated_at, 10, 4, 10, report, {"threshold": 3.5}
    )

    assert first.run_id == second.run_id
    assert first.false_positive_rate == 0.22
