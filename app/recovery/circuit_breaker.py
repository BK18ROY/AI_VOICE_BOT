"""Circuit breaker implementation for resilient external provider invocation."""

import time
from enum import Enum
from typing import Callable, Any, Optional
from app.observability.logger import logger


class CircuitState(str, Enum):
    CLOSED = "closed"        # Healthy, calls pass through
    OPEN = "open"            # Unhealthy, calls fail fast to fallback
    HALF_OPEN = "half_open"  # Probing recovery


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted on an open circuit breaker."""
    pass


class CircuitBreaker:
    """Protects against cascading failures from third-party services."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time: Optional[float] = None

    def record_success(self) -> None:
        """Mark a successful provider invocation."""
        if self.state != CircuitState.CLOSED:
            logger.info("circuit_breaker_recovered", circuit=self.name, previous_state=self.state.value)
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Mark a failed provider invocation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(
            "circuit_breaker_failure",
            circuit=self.name,
            failures=self.failure_count,
            threshold=self.failure_threshold,
            error=str(error) if error else "unknown",
        )
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error("circuit_breaker_opened", circuit=self.name, timeout_seconds=self.recovery_timeout)

    def can_execute(self) -> bool:
        """Determine whether a request should be allowed or failed fast."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self.last_failure_time and (time.time() - self.last_failure_time >= self.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker_half_open_trial", circuit=self.name)
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False
