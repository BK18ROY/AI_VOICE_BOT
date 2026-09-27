"""Unit tests for latency tracking, statistical benchmarking, and audio chunking."""

import pytest
from app.audio.audio_utils import calculate_duration, validate_pcm_chunk
from app.audio.chunking import AudioChunker
from app.observability.latency import LatencyTracker
from app.observability.metrics import MetricsCollector
from scripts.benchmark_latency import compute_stats


def test_latency_tracker_calculations():
    """Verify that LatencyTracker accurately computes millisecond diffs."""
    tracker = LatencyTracker(session_id="test_sess", turn_id=1)

    t0 = 100.000
    tracker.mark("audio_received", timestamp=t0)
    tracker.mark("vad_detected", timestamp=t0 + 0.020)       # 20ms
    tracker.mark("stt_started", timestamp=t0 + 0.025)
    tracker.mark("stt_completed", timestamp=t0 + 0.075)     # 50ms
    tracker.mark("llm_started", timestamp=t0 + 0.080)
    tracker.mark("first_token_received", timestamp=t0 + 0.120) # 40ms TTFT
    tracker.mark("llm_completed", timestamp=t0 + 0.200)       # 120ms total LLM
    tracker.mark("tts_started", timestamp=t0 + 0.130)
    tracker.mark("first_audio_received", timestamp=t0 + 0.180) # 50ms TTFA
    tracker.mark("response_started", timestamp=t0 + 0.180)

    breakdown = tracker.calculate()

    assert breakdown.vad_latency_ms == 20.0
    assert breakdown.stt_latency_ms == 50.0
    assert breakdown.llm_ttft_ms == 40.0
    assert breakdown.llm_total_ms == 120.0
    assert breakdown.tts_ttfa_ms == 50.0
    assert breakdown.end_to_end_ms == 180.0

    d = tracker.to_dict()
    assert d["end_to_end_ms"] == 180.0


def test_compute_stats():
    """Verify statistical metrics calculation."""
    values = [50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    stats = compute_stats(values)

    assert stats["min"] == 50.0
    assert stats["max"] == 100.0
    assert stats["mean"] == 75.0
    assert stats["median"] == 75.0
    assert stats["p95"] >= 90.0

    # Empty list handling
    empty_stats = compute_stats([])
    assert empty_stats["mean"] == 0.0


def test_audio_chunker():
    """Verify AudioChunker splits audio bytes into deterministic 20ms frames."""
    chunker = AudioChunker(session_id="test_sess", sample_rate=16000, chunk_duration_ms=20.0)
    # 20ms at 16kHz 16-bit mono = 16000 * 0.02 * 2 = 640 bytes per chunk
    assert chunker.chunk_size_bytes == 640

    # Send 1500 bytes (should produce two 640-byte chunks and 220 bytes residual)
    incoming = b"\x00\x01" * 750
    chunks = chunker.process_incoming_bytes(incoming)

    assert len(chunks) == 2
    assert len(chunks[0].raw_bytes) == 640
    assert len(chunks[1].raw_bytes) == 640
    assert chunks[0].sequence_number == 1
    assert chunks[1].sequence_number == 2

    # Flush residual
    flushed = chunker.flush()
    assert flushed is not None
    assert len(flushed.raw_bytes) == 220
    assert flushed.sequence_number == 3


def test_audio_utils_validation_and_duration():
    """Verify PCM validation and duration calculation."""
    valid_pcm = b"\x00\x00" * 8000
    assert validate_pcm_chunk(valid_pcm) is True
    assert calculate_duration(valid_pcm, sample_rate=16000) == 0.5

    # Odd byte length is invalid PCM16
    odd_pcm = b"\x00\x00\x01"
    assert validate_pcm_chunk(odd_pcm) is False

    # Empty chunk is invalid
    assert validate_pcm_chunk(b"") is False

    # Oversized chunk
    oversized = b"\x00\x00" * 40000 # 80000 bytes > 65536
    assert validate_pcm_chunk(oversized) is False


def test_metrics_collector():
    """Verify thread-safe MetricsCollector tracks real-time statistics."""
    collector = MetricsCollector()

    collector.session_started()
    collector.session_started()
    assert collector.active_sessions == 2
    assert collector.total_sessions == 2

    collector.record_turn_latency(120.0)
    collector.record_turn_latency(80.0)
    collector.record_barge_in()
    collector.record_failure("stt")
    collector.session_completed(success=True)

    assert collector.active_sessions == 1
    assert collector.successful_sessions == 1
    assert collector.barge_in_count == 1
    assert collector.stt_failures == 1

    resp = collector.get_metrics()
    assert resp.active_sessions == 1
    assert resp.total_sessions == 2
    assert resp.barge_in_count == 1
