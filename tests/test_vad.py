"""Unit tests for Voice Activity Detection (VAD) processor."""

import time
import numpy as np
import pytest
from app.audio.audio_utils import float32_to_pcm16
from app.pipeline.vad_processor import VADProcessor
from app.schemas.audio import VADEventType


def generate_pcm_sine(freq: float = 440.0, duration_s: float = 0.02, sample_rate: int = 16000, amp: float = 0.5) -> bytes:
    """Generate PCM16 sine wave chunk."""
    n = int(duration_s * sample_rate)
    t = np.linspace(0, duration_s, n, endpoint=False)
    sig = amp * np.sin(2 * np.pi * freq * t)
    return float32_to_pcm16(sig.astype(np.float32))


def generate_pcm_silence(duration_s: float = 0.02, sample_rate: int = 16000) -> bytes:
    """Generate PCM16 silence chunk."""
    n = int(duration_s * sample_rate)
    sig = np.zeros(n, dtype=np.float32)
    return float32_to_pcm16(sig)


def test_vad_silence_detection():
    """Verify that pure silence frames are classified as SILENCE."""
    vad = VADProcessor(threshold=0.3)
    silence_frame = generate_pcm_silence(0.02)
    result = vad.process_frame(silence_frame)

    assert result.event_type == VADEventType.SILENCE
    assert not result.is_speaking
    assert result.probability < 0.3


def test_vad_speech_start_and_callbacks():
    """Verify speech activation triggers callback after min duration."""
    start_called = []
    end_called = []

    vad = VADProcessor(
        threshold=0.2,
        min_speech_duration_s=0.04,
        min_silence_duration_s=0.04,
        on_speech_start=lambda: start_called.append(True),
        on_speech_end=lambda: end_called.append(True),
    )

    speech_frame = generate_pcm_sine(freq=300.0, duration_s=0.02, amp=0.4)

    # Frame 1: initial detection
    res1 = vad.process_frame(speech_frame)
    time.sleep(0.05)

    # Frame 2: exceeds min_speech_duration_s
    res2 = vad.process_frame(speech_frame)
    assert res2.is_speaking is True
    assert res2.event_type in (VADEventType.SPEECH_START, VADEventType.SPEECH_ACTIVE)
    assert len(start_called) >= 1

    # Frame 3: speech continues
    res3 = vad.process_frame(speech_frame)
    assert res3.is_speaking is True
    assert res3.event_type == VADEventType.SPEECH_ACTIVE


def test_vad_speech_end_transition():
    """Verify silence following speech triggers SPEECH_END after min silence duration."""
    end_called = []
    vad = VADProcessor(
        threshold=0.2,
        min_speech_duration_s=0.01,
        min_silence_duration_s=0.04,
        on_speech_end=lambda: end_called.append(True),
    )

    speech_frame = generate_pcm_sine(freq=300.0, duration_s=0.02, amp=0.4)
    vad.process_frame(speech_frame)
    time.sleep(0.02)
    vad.process_frame(speech_frame)
    assert vad.is_speaking is True

    # Now feed silence
    silence_frame = generate_pcm_silence(0.02)
    vad.process_frame(silence_frame)
    time.sleep(0.05)
    res_end = vad.process_frame(silence_frame)

    assert vad.is_speaking is False
    assert res_end.event_type == VADEventType.SPEECH_END
    assert len(end_called) == 1
