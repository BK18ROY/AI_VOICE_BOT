"""Cartesia TTS Provider integrating Sonic Multilingual streaming audio."""

import asyncio
from typing import AsyncGenerator, Optional
import httpx
from app.observability.logger import logger
from app.providers.tts.base import BaseTTSProvider
from app.providers.tts.mock_tts import MockTTSProvider
from app.recovery.circuit_breaker import CircuitBreaker


class CartesiaTTSProvider(BaseTTSProvider):
    """Real-time ultra-low latency TTS provider backed by Cartesia Sonic API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: str = "a0e99841-438c-4a64-b679-ae501e7d6091",
        model: str = "sonic-multilingual",
        sample_rate: int = 16000,
        timeout_seconds: float = 4.0,
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.sample_rate = sample_rate
        self.timeout_seconds = timeout_seconds
        self.circuit_breaker = CircuitBreaker(name="cartesia_tts", failure_threshold=3, recovery_timeout=20.0)
        self.fallback = MockTTSProvider(sample_rate=sample_rate)
        self._is_cancelled = False
        self._current_task: Optional[asyncio.Task] = None

    def has_credentials(self) -> bool:
        return bool(self.api_key)

    async def synthesize(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """Synthesize text using Cartesia HTTP API or fallback."""
        if not self.has_credentials() or not self.circuit_breaker.can_execute():
            return await self.fallback.synthesize(text, voice_id)

        target_voice = voice_id or self.voice_id
        url = "https://api.cartesia.ai/tts/bytes"
        headers = {
            "X-API-Key": self.api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json",
        }
        payload = {
            "model_id": self.model,
            "transcript": text,
            "voice": {"mode": "id", "id": target_voice},
            "output_format": {
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": self.sample_rate,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    self.circuit_breaker.record_success()
                    return resp.content
                else:
                    raise RuntimeError(f"Cartesia returned HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            self.circuit_breaker.record_failure(e)
            logger.warning("cartesia_synthesize_failed_falling_back", error=str(e))
            return await self.fallback.synthesize(text, voice_id)

    async def synthesize_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """Stream chunks from Cartesia or fallback with active cancellation."""
        self._is_cancelled = False

        if not self.has_credentials() or not self.circuit_breaker.can_execute():
            async for audio_chunk in self.fallback.synthesize_stream(text_stream, voice_id):
                if self._is_cancelled:
                    break
                yield audio_chunk
            return

        # Aggregate tokens into small coherent sentences or clauses for low latency streaming
        buffer = []
        async for token in text_stream:
            if self._is_cancelled:
                break
            buffer.append(token)
            if any(p in token for p in [".", ",", "!", "?", "\n"]) or len(buffer) >= 6:
                phrase = "".join(buffer).strip()
                buffer.clear()
                if phrase:
                    audio = await self.synthesize(phrase, voice_id)
                    if self._is_cancelled:
                        break
                    if audio:
                        yield audio

        # Remainder
        if buffer and not self._is_cancelled:
            phrase = "".join(buffer).strip()
            if phrase:
                audio = await self.synthesize(phrase, voice_id)
                if not self._is_cancelled and audio:
                    yield audio

    def cancel(self) -> None:
        """Interrupt and halt active speech synthesis."""
        self._is_cancelled = True
        self.fallback.cancel()

    async def is_ready(self) -> bool:
        return self.has_credentials()
