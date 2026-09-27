"""Unit tests for Text-to-Speech (TTS) provider and processor."""

import asyncio
import pytest
from app.audio.audio_utils import validate_pcm_chunk
from app.observability.latency import LatencyTracker
from app.pipeline.tts_processor import TTSProcessor
from app.providers.tts.mock_tts import MockTTSProvider


@pytest.mark.asyncio
async def test_mock_tts_single_synthesis():
    """Verify single synthesis returns valid PCM audio bytes."""
    tts = MockTTSProvider(sample_rate=16000)
    audio = await tts.synthesize("Hello world.")

    assert len(audio) > 0
    # Must be 16-bit PCM (multiple of 2 bytes)
    assert len(audio) % 2 == 0
    assert validate_pcm_chunk(audio) is True


@pytest.mark.asyncio
async def test_mock_tts_streaming():
    """Verify streaming token synthesis yields successive audio chunks."""
    tts = MockTTSProvider(sample_rate=16000)

    async def token_generator():
        words = ["Your", "warranty", "is", "active", "until", "next", "year.", "Thank", "you."]
        for w in words:
            yield w + " "
            await asyncio.sleep(0.01)

    chunks = []
    async for chunk in tts.synthesize_stream(token_generator()):
        chunks.append(chunk)

    assert len(chunks) >= 1
    total_bytes = sum(len(c) for c in chunks)
    assert total_bytes > 0
    for c in chunks:
        assert len(c) % 2 == 0


@pytest.mark.asyncio
async def test_mock_tts_cancellation():
    """Verify cancellation stops audio generation immediately."""
    tts = MockTTSProvider(sample_rate=16000)

    async def long_token_generator():
        for i in range(50):
            yield f"token_{i} "
            await asyncio.sleep(0.02)

    chunks = []
    async for chunk in tts.synthesize_stream(long_token_generator()):
        chunks.append(chunk)
        # Cancel right after first chunk
        tts.cancel()

    # Should have stopped early
    assert len(chunks) < 10


@pytest.mark.asyncio
async def test_tts_processor_latency_tracking():
    """Verify TTSProcessor marks first audio and response start milestones."""
    tts = MockTTSProvider(sample_rate=16000)
    processor = TTSProcessor(provider=tts)
    tracker = LatencyTracker(session_id="test_tts_session")
    tracker.mark("audio_received")
    tracker.mark("llm_started")

    async def sample_tokens():
        yield "Your EMI installment of 24,500 rupees is confirmed."

    chunks = []
    async for chunk in processor.stream_audio_from_tokens(sample_tokens(), tracker=tracker):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert tracker.milestones.tts_started is not None
    assert tracker.milestones.first_audio_received is not None
    assert tracker.milestones.response_started is not None
    breakdown = tracker.calculate()
    assert breakdown.tts_ttfa_ms is not None
    assert breakdown.tts_ttfa_ms >= 0.0
