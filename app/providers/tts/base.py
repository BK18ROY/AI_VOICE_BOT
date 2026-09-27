"""Base abstraction for Text-To-Speech providers."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional


class BaseTTSProvider(ABC):
    """Abstract interface for speech synthesis engines."""

    @abstractmethod
    async def synthesize(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """Synthesize complete text string to PCM16 audio bytes."""
        pass

    @abstractmethod
    async def synthesize_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """Stream synthesized audio chunks as tokens/phrases arrive."""
        pass

    @abstractmethod
    def cancel(self) -> None:
        """Immediately abort active synthesis (used for barge-in / interruption)."""
        pass

    @abstractmethod
    async def is_ready(self) -> bool:
        """Check provider readiness."""
        pass
