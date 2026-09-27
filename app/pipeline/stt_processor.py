"""Speech-to-Text pipeline processor."""

import asyncio
from typing import AsyncGenerator, Optional
from app.observability.latency import LatencyTracker
from app.observability.logger import logger
from app.observability.metrics import metrics_collector
from app.providers.stt.base import BaseSTTProvider, STTResult
from app.recovery.retry import async_retry


class STTProcessor:
    """Wraps STT engine with latency instrumentation, timeouts, and recovery."""

    def __init__(self, provider: BaseSTTProvider, timeout_seconds: float = 3.0):
        self.provider = provider
        self.timeout_seconds = timeout_seconds

    async def transcribe_utterance(
        self,
        audio_bytes: bytes,
        tracker: Optional[LatencyTracker] = None,
        sample_rate: int = 16000,
    ) -> STTResult:
        """Transcribe speech segment with timeout and latency recording."""
        if tracker:
            tracker.mark("stt_started")

        try:
            # Wrap provider call in timeout
            result = await asyncio.wait_for(
                async_retry(
                    self.provider.transcribe,
                    audio_bytes,
                    sample_rate=sample_rate,
                    max_retries=1,
                    component_name="stt",
                ),
                timeout=self.timeout_seconds,
            )

            if tracker:
                tracker.mark("stt_completed")

            return result

        except Exception as e:
            metrics_collector.record_failure("stt")
            logger.error("stt_processor_failure", error=str(e))
            if tracker:
                tracker.mark("stt_completed")
            return STTResult(text="", is_final=True, confidence=0.0)
