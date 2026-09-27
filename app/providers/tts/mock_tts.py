"""Deterministic Mock TTS Provider generating PCM16 audio frames."""

import asyncio
from typing import AsyncGenerator, Optional
import numpy as np
from app.audio.audio_utils import float32_to_pcm16
from app.providers.tts.base import BaseTTSProvider


class MockTTSProvider(BaseTTSProvider):
    """Mock TTS generating valid 16kHz PCM16 audio buffers without external API dependencies."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._cancelled = False

    def _generate_synthetic_tone(self, duration_s: float = 0.2, freq: float = 440.0) -> bytes:
        """Create a soft, windowed synthetic PCM frame to simulate vocal audio."""
        num_samples = int(self.sample_rate * duration_s)
        t = np.linspace(0, duration_s, num_samples, endpoint=False)
        # Soft tone with hanning window to prevent clipping
        waveform = 0.2 * np.sin(2 * np.pi * freq * t) * np.hanning(num_samples)
        return float32_to_pcm16(waveform.astype(np.float32))

    async def synthesize(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """Synthesize text into a single PCM16 audio payload."""
        self._cancelled = False
        # Simulate ~40ms synthesis latency
        await asyncio.sleep(0.04)
        if self._cancelled:
            return b""
        duration = min(max(len(text) * 0.05, 0.3), 3.0)
        return self._generate_synthetic_tone(duration_s=duration)

    async def synthesize_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """Stream simulated audio chunks chunk-by-chunk."""
        self._cancelled = False
        accumulated_text = ""

        async for chunk in text_stream:
            if self._cancelled:
                break
            accumulated_text += chunk

            # When a phrase or sufficient words are received, emit an audio slice
            if len(accumulated_text) >= 15 or any(p in chunk for p in [".", ",", "!", "?", "\n"]):
                await asyncio.sleep(0.03)  # TTFA / synthesis latency per slice
                if self._cancelled:
                    break
                slice_bytes = self._generate_synthetic_tone(duration_s=0.25, freq=300.0)
                yield slice_bytes
                accumulated_text = ""

        # Emit remaining text
        if accumulated_text and not self._cancelled:
            await asyncio.sleep(0.02)
            if not self._cancelled:
                yield self._generate_synthetic_tone(duration_s=0.2, freq=300.0)

    def cancel(self) -> None:
        """Interrupt active TTS synthesis immediately."""
        self._cancelled = True

    async def is_ready(self) -> bool:
        return True
