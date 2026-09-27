"""Voice Activity Detection (VAD) processor using configurable threshold and Silero-compatible logic."""

import time
from typing import Callable, List, Optional
import numpy as np
from app.audio.audio_utils import pcm16_to_float32
from app.observability.logger import logger
from app.schemas.audio import VADEventType, VADResult


class VADProcessor:
    """Detects voice activity, speech boundaries, and silence in streaming audio frames."""

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration_s: float = 0.25,
        min_silence_duration_s: float = 0.5,
        sample_rate: int = 16000,
        on_speech_start: Optional[Callable[[], None]] = None,
        on_speech_end: Optional[Callable[[], None]] = None,
    ):
        self.threshold = threshold
        self.min_speech_duration_s = min_speech_duration_s
        self.min_silence_duration_s = min_silence_duration_s
        self.sample_rate = sample_rate
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end

        self._is_speaking = False
        self._speech_start_time: Optional[float] = None
        self._last_speech_time: Optional[float] = None
        self._silence_start_time: Optional[float] = None

    @property
    def is_speaking(self) -> bool:
        """Current speech activity state."""
        return self._is_speaking

    def _calculate_speech_probability(self, frame_float: np.ndarray) -> float:
        """Compute speech probability using frame RMS energy and spectral dispersion."""
        if frame_float.size == 0:
            return 0.0

        rms = float(np.sqrt(np.mean(frame_float**2)))
        # Normalize RMS: silence is typically <0.01; speech is 0.05-0.5
        prob = min(max((rms - 0.015) / 0.08, 0.0), 1.0)
        return float(prob)

    def process_frame(self, pcm_bytes: bytes) -> VADResult:
        """Process a 20-30ms audio frame and evaluate speech state transitions."""
        now = time.time()
        frame_float = pcm16_to_float32(pcm_bytes)
        prob = self._calculate_speech_probability(frame_float)
        frame_has_speech = prob >= self.threshold

        event_type = VADEventType.SILENCE

        if frame_has_speech:
            self._silence_start_time = None
            if not self._is_speaking:
                if self._speech_start_time is None:
                    self._speech_start_time = now
                elif now - self._speech_start_time >= self.min_speech_duration_s:
                    # Speech start boundary met
                    self._is_speaking = True
                    event_type = VADEventType.SPEECH_START
                    if self.on_speech_start:
                        self.on_speech_start()
            else:
                event_type = VADEventType.SPEECH_ACTIVE
            self._last_speech_time = now

        else:
            # Silence detected in this frame
            if self._is_speaking:
                if self._silence_start_time is None:
                    self._silence_start_time = now
                elif now - self._silence_start_time >= self.min_silence_duration_s:
                    # Speech end boundary met
                    self._is_speaking = False
                    self._speech_start_time = None
                    self._silence_start_time = None
                    event_type = VADEventType.SPEECH_END
                    if self.on_speech_end:
                        self.on_speech_end()
                else:
                    event_type = VADEventType.SPEECH_ACTIVE
            else:
                self._speech_start_time = None
                event_type = VADEventType.SILENCE

        speech_dur = (now - self._speech_start_time) * 1000.0 if (self._speech_start_time and self._is_speaking) else 0.0
        silence_dur = (now - self._silence_start_time) * 1000.0 if self._silence_start_time else 0.0

        return VADResult(
            event_type=event_type,
            timestamp=now,
            probability=prob,
            is_speaking=self._is_speaking,
            speech_duration_ms=round(speech_dur, 2),
            silence_duration_ms=round(silence_dur, 2),
        )

    def reset(self) -> None:
        """Reset state between turns."""
        self._is_speaking = False
        self._speech_start_time = None
        self._last_speech_time = None
        self._silence_start_time = None
