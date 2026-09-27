"""Unit tests for Speech-To-Text (STT) provider and processor."""

import asyncio
import pytest
from app.observability.latency import LatencyTracker
from app.pipeline.stt_processor import STTProcessor
from app.providers.stt.base import BaseSTTProvider, STTResult
from app.providers.stt.mock_stt import MockSTTProvider


@pytest.mark.asyncio
async def test_mock_stt_transcribe():
    """Verify mock STT returns accurate transcript and preset queue."""
    provider = MockSTTProvider(default_response="Default utterance")
    dummy_audio = b"\x00\x00" * 8000  # 0.5s of 16kHz audio

    res1 = await provider.transcribe(dummy_audio)
    assert res1.text == "Default utterance"
    assert res1.is_final is True
    assert res1.confidence > 0.9

    provider.set_next_transcripts(["Custom phrase 1", "Custom phrase 2"])
    res2 = await provider.transcribe(dummy_audio)
    assert res2.text == "Custom phrase 1"

    res3 = await provider.transcribe(dummy_audio)
    assert res3.text == "Custom phrase 2"


@pytest.mark.asyncio
async def test_mock_stt_streaming():
    """Verify mock STT streaming yields partial and final results."""
    provider = MockSTTProvider(default_response="Warranty for SN-5521")

    async def fake_audio_stream():
        for _ in range(3):
            yield b"\x00\x00" * 320

    stream_results = []
    async for item in provider.transcribe_stream(fake_audio_stream()):
        stream_results.append(item)

    assert len(stream_results) >= 2
    assert stream_results[-1].is_final is True
    assert "Warranty" in stream_results[-1].text


@pytest.mark.asyncio
async def test_stt_processor_with_tracker():
    """Verify STTProcessor marks latency metrics correctly."""
    provider = MockSTTProvider(default_response="Hello support")
    processor = STTProcessor(provider=provider, timeout_seconds=2.0)
    tracker = LatencyTracker(session_id="test_session")

    dummy_audio = b"\x00\x00" * 1600
    result = await processor.transcribe_utterance(dummy_audio, tracker=tracker)

    assert result.text == "Hello support"
    assert tracker.milestones.stt_started is not None
    assert tracker.milestones.stt_completed is not None
    breakdown = tracker.calculate()
    assert breakdown.stt_latency_ms is not None
    assert breakdown.stt_latency_ms >= 0.0


@pytest.mark.asyncio
async def test_stt_processor_timeout_handling():
    """Verify STTProcessor gracefully handles slow or hanging providers."""
    class HangingSTTProvider(BaseSTTProvider):
        async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> STTResult:
            await asyncio.sleep(2.0)
            return STTResult(text="Should have timed out", is_final=True)

        async def transcribe_stream(self, audio_stream, sample_rate=16000):
            yield STTResult(text="", is_final=True)

        async def is_ready(self) -> bool:
            return True

    processor = STTProcessor(provider=HangingSTTProvider(), timeout_seconds=0.05)
    tracker = LatencyTracker(session_id="test_session")
    result = await processor.transcribe_utterance(b"\x00\x00", tracker=tracker)

    # Should catch timeout and return fallback STTResult cleanly
    assert result.text == ""
    assert result.confidence == 0.0
