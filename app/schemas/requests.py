"""Incoming request schemas for HTTP and WebSocket messages."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.schemas.conversation import LanguageCode


class ClientMessageType(str, Enum):
    """Client-to-server WebSocket message types."""
    SESSION_START = "session_start"
    AUDIO_CHUNK = "audio_chunk"
    TEXT_INPUT = "text_input"
    BARGE_IN = "barge_in"
    SESSION_END = "session_end"
    PING = "ping"


class SessionStartRequest(BaseModel):
    """Initiates a new voice assistant session."""
    session_id: Optional[str] = None
    caller_id: str = "customer_default"
    initial_language: LanguageCode = LanguageCode.EN
    workflow_hint: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WebSocketClientMessage(BaseModel):
    """Normalized payload envelope from WebSocket client."""
    type: ClientMessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
