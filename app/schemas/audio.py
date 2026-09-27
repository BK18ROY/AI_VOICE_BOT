"""Audio-related schemas and data models."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AudioFormat(str, Enum):
    """Supported audio encoding formats."""
    PCM16 = "pcm16"
    WAV = "wav"
    FLOAT32 = "float32"


class AudioChunk(BaseModel):
    """Schema representing an audio slice in streaming pipeline."""

    session_id: str = Field(description="Unique session/call ID")
    sequence_number: int = Field(default=0, description="Monotonically increasing sequence number")
    timestamp: float = Field(description="Unix epoch timestamp in seconds")
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of channels (1=mono, 2=stereo)")
    format: AudioFormat = Field(default=AudioFormat.PCM16)
    duration_ms: float = Field(default=0.0, description="Duration in milliseconds")
    raw_bytes: bytes = Field(default=b"", description="Raw audio bytes (PCM16 mono)")

    def get_chunk_id(self) -> str:
        """Generate a safe, unique chunk identifier string."""
        return f"{self.session_id}_{self.sequence_number}_{int(self.timestamp * 1000)}"


class VADEventType(str, Enum):
    """VAD detection events."""
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    SPEECH_ACTIVE = "speech_active"
    SILENCE = "silence"


class VADResult(BaseModel):
    """Voice Activity Detection result for an audio segment."""

    event_type: VADEventType
    timestamp: float
    probability: float = Field(ge=0.0, le=1.0)
    is_speaking: bool
    speech_duration_ms: float = 0.0
    silence_duration_ms: float = 0.0
