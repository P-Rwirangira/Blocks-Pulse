import pytest

from blockpulse.chain_health.application.circuit_breaker import EndpointCircuitBreaker


def test_circuit_reopens_after_cooldown() -> None:
    now = 0.0
    breaker = EndpointCircuitBreaker(2, 10, clock=lambda: now)
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.allow_request() is False

    now = 10.0
    assert breaker.allow_request() is True
    breaker.record_success()
    assert breaker.allow_request() is True


def test_circuit_configuration_is_validated() -> None:
    with pytest.raises(ValueError, match="threshold"):
        EndpointCircuitBreaker(0)
    with pytest.raises(ValueError, match="cooldown"):
        EndpointCircuitBreaker(1, 0)
