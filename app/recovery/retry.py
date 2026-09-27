"""Asynchronous retry helper with exponential backoff and jitter."""

import asyncio
import random
from typing import Any, Callable, Coroutine, Tuple, Type, TypeVar
from app.observability.logger import logger

T = TypeVar("T")


async def async_retry(
    coro_fn: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    max_retries: int = 2,
    base_delay: float = 0.2,
    max_delay: float = 2.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    component_name: str = "service",
    **kwargs: Any,
) -> T:
    """Execute coroutine with exponential backoff retry."""
    attempt = 0
    delay = base_delay

    while True:
        try:
            return await coro_fn(*args, **kwargs)
        except retry_exceptions as e:
            attempt += 1
            if attempt > max_retries:
                logger.error(
                    "retry_exhausted",
                    component=component_name,
                    attempts=attempt,
                    error=str(e),
                )
                raise

            # Add jitter to delay
            jittered_delay = delay * (0.8 + 0.4 * random.random())
            logger.warning(
                "retry_attempt",
                component=component_name,
                attempt=attempt,
                max_retries=max_retries,
                delay_s=round(jittered_delay, 3),
                error=str(e),
            )
            await asyncio.sleep(jittered_delay)
            delay = min(delay * 2.0, max_delay)
