"""DeepSpeech-compatible STT Provider interface."""

import asyncio
import os
from typing import AsyncGenerator, Optional
import numpy as np
from app.observability.logger import logger
from app.providers.stt.base import BaseSTTProvider, STTResult


class DeepSpeechProvider(BaseSTTProvider):
    """Integrates DeepSpeech acoustic model behind the standard provider interface."""

    def __init__(self, model_path: Optional[str] = None, scorer_path: Optional[str] = None):
        self.model_path = model_path
        self.scorer_path = scorer_path
        self._model = None
        self._initialized = False

    def _initialize_model(self) -> bool:
        """Lazily initialize DeepSpeech model if available on host."""
        if self._initialized:
            return self._model is not None

        self._initialized = True
        if not self.model_path or not os.path.exists(self.model_path):
            logger.warning(
                "deepspeech_model_missing",
                path=self.model_path,
                msg="DeepSpeech model file not found; provider will operate in graceful fallback mode.",
            )
            return False

        try:
            import deepspeech  # type: ignore
            self._model = deepspeech.Model(self.model_path)
            if self.scorer_path and os.path.exists(self.scorer_path):
                self._model.enableExternalScorer(self.scorer_path)
            logger.info("deepspeech_initialized_successfully", model_path=self.model_path)
            return True
        except ImportError:
            logger.warning(
                "deepspeech_package_not_installed",
                msg="deepspeech python library not installed in current environment.",
            )
            return False
        except Exception as e:
            logger.error("deepspeech_init_failed", error=str(e))
            return False

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> STTResult:
        """Transcribe PCM16 audio using DeepSpeech or fallback."""
        if not self._initialize_model():
            # Graceful fallback when model is not downloaded
            from app.providers.stt.mock_stt import MockSTTProvider
            return await MockSTTProvider().transcribe(audio_bytes, sample_rate)

        # Offload CPU-heavy inference to threadpool
        def _run_inference():
            audio_16 = np.frombuffer(audio_bytes, dtype=np.int16)
            return self._model.stt(audio_16)

        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, _run_inference)
        return STTResult(text=text, is_final=True, confidence=0.9)

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        sample_rate: int = 16000,
    ) -> AsyncGenerator[STTResult, None]:
        """Stream audio chunks through DeepSpeech streaming decoder context."""
        if not self._initialize_model():
            from app.providers.stt.mock_stt import MockSTTProvider
            async for res in MockSTTProvider().transcribe_stream(audio_stream, sample_rate):
                yield res
            return

        loop = asyncio.get_running_loop()
        stream_ctx = await loop.run_in_executor(None, self._model.createStream)

        try:
            async for chunk in audio_stream:
                audio_16 = np.frombuffer(chunk, dtype=np.int16)
                await loop.run_in_executor(None, stream_ctx.feedAudioContent, audio_16)
                intermediate = await loop.run_in_executor(None, stream_ctx.intermediateDecode)
                if intermediate:
                    yield STTResult(text=intermediate, is_final=False)

            final_text = await loop.run_in_executor(None, stream_ctx.finishStream)
            yield STTResult(text=final_text, is_final=True)
        except Exception as e:
            logger.error("deepspeech_stream_error", error=str(e))
            yield STTResult(text="", is_final=True)

    async def is_ready(self) -> bool:
        return self._initialize_model()
