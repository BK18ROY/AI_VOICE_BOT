"""Deterministic Mock STT Provider for testing and local zero-dependency operation."""

import asyncio
import time
from typing import AsyncGenerator, List, Optional
from app.providers.stt.base import BaseSTTProvider, STTResult


class MockSTTProvider(BaseSTTProvider):
    """Mock STT Provider simulating real-time speech recognition."""

    def __init__(self, default_response: str = "Can you check the warranty status for SN-5521?"):
        self.default_response = default_response
        self._preset_queue: List[str] = []

    def set_next_transcripts(self, transcripts: List[str]) -> None:
        """Queue specific phrases to be emitted on successive transcriptions."""
        self._preset_queue = list(transcripts)

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> STTResult:
        """Simulate fast transcription of audio bytes."""
        # Realistic small processing delay (e.g. 50ms)
        await asyncio.sleep(0.05)

        text = self._preset_queue.pop(0) if self._preset_queue else self.default_response
        return STTResult(
            text=text,
            is_final=True,
            confidence=0.98,
            duration_ms=50.0,
        )

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        sample_rate: int = 16000,
    ) -> AsyncGenerator[STTResult, None]:
        """Simulate partial and final transcription results over a stream."""
        target_text = self._preset_queue.pop(0) if self._preset_queue else self.default_response
        words = target_text.split()

        accumulated = []
        async for _ in audio_stream:
            if words:
                accumulated.append(words.pop(0))
                yield STTResult(
                    text=" ".join(accumulated),
                    is_final=False,
                    confidence=0.85,
                )
                await asyncio.sleep(0.03)

        # Remaining words
        if words:
            accumulated.extend(words)

        yield STTResult(
            text=" ".join(accumulated),
            is_final=True,
            confidence=0.98,
        )

    async def is_ready(self) -> bool:
        return True
