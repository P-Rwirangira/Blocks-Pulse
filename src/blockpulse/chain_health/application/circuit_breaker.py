"""Endpoint circuit-breaker state for unreliable public RPCs."""

import time
from collections.abc import Callable


class EndpointCircuitBreaker:
    """Open after repeated failures and allow a later recovery probe."""

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold <= 0:
            raise ValueError("failure threshold must be positive")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown must be positive")
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.clock = clock
        self.consecutive_failures = 0
        self.opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        """Return whether requests should currently be skipped."""

        if self.opened_at is None:
            return False
        return self.clock() - self.opened_at < self.cooldown_seconds

    def allow_request(self) -> bool:
        """Allow normal traffic or one recovery probe after cooldown."""

        if self.opened_at is None:
            return True
        if self.clock() - self.opened_at >= self.cooldown_seconds:
            self.opened_at = None
            self.consecutive_failures = 0
            return True
        return False

    def record_success(self) -> None:
        """Close the circuit after a successful request."""

        self.consecutive_failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        """Count a failure and open after the configured threshold."""

        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.opened_at = self.clock()
