"""Text-to-Speech pipeline processor with streaming audio generation."""

import asyncio
from typing import AsyncGenerator, Optional
from app.observability.latency import LatencyTracker
from app.observability.logger import logger
from app.observability.metrics import metrics_collector
from app.providers.tts.base import BaseTTSProvider


class TTSProcessor:
    """Processes streamed text into audio frames with latency metrics and cancellation."""

    def __init__(self, provider: BaseTTSProvider, timeout_seconds: float = 4.0):
        self.provider = provider
        self.timeout_seconds = timeout_seconds

    async def stream_audio_from_tokens(
        self,
        token_stream: AsyncGenerator[str, None],
        tracker: Optional[LatencyTracker] = None,
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """Convert stream of LLM tokens into streaming audio slices."""
        if tracker:
            tracker.mark("tts_started")

        first_audio_marked = False

        try:
            async for audio_chunk in self.provider.synthesize_stream(token_stream, voice_id=voice_id):
                if not first_audio_marked:
                    if tracker:
                        tracker.mark("first_audio_received")
                        tracker.mark("response_started")
                    first_audio_marked = True

                yield audio_chunk

        except asyncio.CancelledError:
            logger.info("tts_synthesis_cancelled_due_to_interruption")
            self.cancel()
            raise
        except Exception as e:
            metrics_collector.record_failure("tts")
            logger.error("tts_processor_failure", error=str(e))
            if tracker and not first_audio_marked:
                tracker.mark("first_audio_received")
                tracker.mark("response_started")

    def cancel(self) -> None:
        """Halt speech synthesis immediately."""
        self.provider.cancel()
