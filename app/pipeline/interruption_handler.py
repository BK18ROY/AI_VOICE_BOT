"""Interruption (Barge-in) detector and lifecycle manager."""

import asyncio
from typing import Callable, List, Optional
from app.observability.logger import logger
from app.observability.metrics import metrics_collector


class InterruptionHandler:
    """Detects barge-in when caller speaks while bot is outputting audio, cancels playback, and resets pipelines."""

    def __init__(
        self,
        on_interrupt_callback: Optional[Callable[[], None]] = None,
    ):
        self.on_interrupt_callback = on_interrupt_callback
        self._bot_speaking = False
        self._active_tts_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.interruption_count = 0

    @property
    def bot_is_speaking(self) -> bool:
        return self._bot_speaking

    def set_bot_speaking(self, speaking: bool, active_task: Optional[asyncio.Task] = None) -> None:
        """Update bot speech output status."""
        self._bot_speaking = speaking
        self._active_tts_task = active_task if speaking else None

    async def handle_user_speech_start(self, session_id: str) -> bool:
        """Invoked by VAD or transport when user starts talking."""
        async with self._lock:
            if not self._bot_speaking:
                return False

            # Barge-in detected!
            self.interruption_count += 1
            metrics_collector.record_barge_in()
            logger.info("barge_in_interruption_detected", session_id=session_id, count=self.interruption_count)

            # 1. Cancel active bot TTS task
            if self._active_tts_task and not self._active_tts_task.done():
                self._active_tts_task.cancel()
                logger.info("active_tts_task_cancelled", session_id=session_id)

            # 2. Reset bot speech state
            self._bot_speaking = False
            self._active_tts_task = None

            # 3. Fire registered interruption callback (flush buffers, emit websocket event)
            if self.on_interrupt_callback:
                try:
                    res = self.on_interrupt_callback()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as e:
                    logger.error("interruption_callback_error", error=str(e))

            return True

    def reset(self) -> None:
        """Reset handler state."""
        self._bot_speaking = False
        self._active_tts_task = None
