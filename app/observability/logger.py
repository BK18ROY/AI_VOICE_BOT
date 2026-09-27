"""Centralized structured logger for AI Voice Bot."""

import logging
import os
import sys
from typing import Any, Dict, Optional
import structlog


def setup_logger(log_level: str = "INFO", structured: bool = True) -> structlog.BoundLogger:
    """Configure centralized logger with structlog and standard logging."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
        force=True,
    )

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if structured:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("ai_voice_bot")


# Global base logger
logger = setup_logger(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    structured=os.getenv("ENABLE_STRUCTURED_LOGS", "false").lower() == "true",
)


def get_session_logger(session_id: str, **kwargs: Any) -> structlog.BoundLogger:
    """Return a logger bound with session ID and arbitrary extra context."""
    # Sanitize to never leak API keys or tokens
    safe_kwargs = {
        k: (v if not any(secret in k.lower() for secret in ["key", "token", "auth", "secret", "password"]) else "[REDACTED]")
        for k, v in kwargs.items()
    }
    return logger.bind(session_id=session_id, **safe_kwargs)
