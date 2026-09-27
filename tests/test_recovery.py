"""Unit tests for recovery, circuit breaker, retry logic, and fallback responses."""

import asyncio
import time
import pytest
from app.recovery.circuit_breaker import CircuitBreaker, CircuitState
from app.recovery.fallback import get_fallback_response
from app.recovery.retry import async_retry
from app.schemas.conversation import LanguageCode


def test_circuit_breaker_transitions():
    """Verify circuit breaker lifecycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_timeout=0.1)

    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # Record 1st failure
    cb.record_failure(Exception("Fail 1"))
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # Record 2nd failure -> Trips open
    cb.record_failure(Exception("Fail 2"))
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # Wait for recovery timeout
    time.sleep(0.15)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Success in half open -> closes circuit
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_async_retry_success_after_failure():
    """Verify async_retry recovers after transient failures."""
    attempts = 0

    async def transient_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ConnectionError("Temporary connection drop")
        return "SUCCESS"

    result = await async_retry(transient_operation, max_retries=2, base_delay=0.01)
    assert result == "SUCCESS"
    assert attempts == 2


@pytest.mark.asyncio
async def test_async_retry_exhausted():
    """Verify async_retry re-raises exception when max retries exceeded."""
    async def always_fails():
        raise ValueError("Permanent configuration failure")

    with pytest.raises(ValueError, match="Permanent configuration failure"):
        await async_retry(always_fails, max_retries=2, base_delay=0.01)


def test_fallback_responses_multilingual():
    """Verify fallback messages are accurately localized across EN, HI, and HINGLISH."""
    # LLM error
    msg_en = get_fallback_response("llm_error", language=LanguageCode.EN)
    assert "network" in msg_en.lower() or "delay" in msg_en.lower()

    msg_hi = get_fallback_response("llm_error", language=LanguageCode.HI)
    assert "परेशानी" in msg_hi or "प्रतीक्षा" in msg_hi

    msg_hinglish = get_fallback_response("llm_error", language=LanguageCode.HINGLISH)
    assert "network" in msg_hinglish.lower() or "batata" in msg_hinglish.lower()

    # Unintelligible
    msg_unintelligible = get_fallback_response("unintelligible", language=LanguageCode.EN)
    assert "repeat" in msg_unintelligible.lower()

    # Empty transcript
    msg_empty = get_fallback_response("empty_transcript", language=LanguageCode.EN)
    assert "still there" in msg_empty.lower()
