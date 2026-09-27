"""Lightweight distributed tracing and span context."""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Span(BaseModel):
    """Execution span representing an operational phase."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    def finish(self, error: Optional[str] = None) -> None:
        self.end_time = time.perf_counter()
        self.duration_ms = round((self.end_time - self.start_time) * 1000.0, 2)
        if error:
            self.error = error


class SessionTracer:
    """Manages spans for an active voice call session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.spans: List[Span] = []

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Span:
        """Begin a new named span."""
        span = Span(
            name=name,
            start_time=time.perf_counter(),
            attributes=attributes or {},
        )
        self.spans.append(span)
        return span

    def to_dict(self) -> List[Dict[str, Any]]:
        return [s.model_dump() for s in self.spans]
