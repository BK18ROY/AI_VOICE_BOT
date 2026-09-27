"""Base abstraction for Speech-To-Text providers."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from pydantic import BaseModel, Field


class STTResult(BaseModel):
    """Transcription output model."""
    text: str
    is_final: bool = True
    confidence: float = 1.0
    language: Optional[str] = None
    duration_ms: Optional[float] = None


class BaseSTTProvider(ABC):
    """Abstract interface for Speech-to-Text engines."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> STTResult:
        """Transcribe a complete segment of PCM16 audio."""
        pass

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        sample_rate: int = 16000,
    ) -> AsyncGenerator[STTResult, None]:
        """Stream transcription partials and final text."""
        pass

    @abstractmethod
    async def is_ready(self) -> bool:
        """Health/readiness check for provider."""
        pass
