"""Outgoing response and event schemas for HTTP and WebSocket."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.conversation import ConversationTurn, LanguageCode, IntentType


class ServerEventType(str, Enum):
    """Server-to-client WebSocket event types."""
    SESSION_START = "session_start"
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    TRANSCRIPT_PARTIAL = "transcript_partial"
    TRANSCRIPT_FINAL = "transcript_final"
    LLM_START = "llm_start"
    LLM_TOKEN = "llm_token"
    LLM_COMPLETE = "llm_complete"
    TTS_START = "tts_start"
    TTS_AUDIO = "tts_audio"
    TTS_COMPLETE = "tts_complete"
    BARGE_IN = "barge_in"
    ERROR = "error"
    SESSION_END = "session_end"
    PONG = "pong"


class WebSocketServerEvent(BaseModel):
    """Event pushed to client over WebSocket."""
    event: ServerEventType
    session_id: str
    timestamp: float
    data: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: Optional[float] = None


class SessionSummary(BaseModel):
    """Post-call summary report."""
    session_id: str
    caller_id: str
    start_time: float
    end_time: float
    duration_seconds: float
    total_turns: int
    interruption_count: int
    detected_language: LanguageCode
    primary_intent: IntentType
    active_workflow: Optional[str] = None
    provider_failures: Dict[str, int] = Field(default_factory=dict)
    average_turn_latency_ms: float = 0.0
    p95_turn_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    history: List[ConversationTurn] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Service health response."""
    status: str = "healthy"
    service: str = "ai-voice-bot"
    timestamp: float
    version: str = "1.0.0"


class ReadyResponse(BaseModel):
    """Detailed readiness check response."""
    status: str
    providers: Dict[str, str]
    environment: str = "local"
    details: Dict[str, Any] = Field(default_factory=dict)


class MetricsResponse(BaseModel):
    """Real-time server metrics."""
    active_sessions: int
    total_sessions: int
    successful_sessions: int
    failed_sessions: int
    average_latency_ms: float
    p95_latency_ms: float
    barge_in_count: int
    stt_failures: int
    llm_failures: int
    tts_failures: int
