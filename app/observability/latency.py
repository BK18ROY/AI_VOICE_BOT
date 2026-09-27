"""Fine-grained latency tracking across real-time voice pipeline stages."""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LatencyMilestones(BaseModel):
    """Timestamps (monotonic or unix) recorded along the pipeline."""
    audio_received: Optional[float] = None
    vad_detected: Optional[float] = None
    stt_started: Optional[float] = None
    stt_completed: Optional[float] = None
    llm_started: Optional[float] = None
    first_token_received: Optional[float] = None
    llm_completed: Optional[float] = None
    tts_started: Optional[float] = None
    first_audio_received: Optional[float] = None
    response_started: Optional[float] = None


class LatencyBreakdown(BaseModel):
    """Calculated latencies in milliseconds."""
    vad_latency_ms: Optional[float] = None
    stt_latency_ms: Optional[float] = None
    llm_ttft_ms: Optional[float] = Field(None, description="Time to first LLM token")
    llm_total_ms: Optional[float] = Field(None, description="Total LLM generation duration")
    tts_ttfa_ms: Optional[float] = Field(None, description="Time to first synthesized audio chunk")
    tts_total_ms: Optional[float] = Field(None, description="Total TTS duration")
    end_to_end_ms: Optional[float] = Field(None, description="Total caller-to-response latency")


class LatencyTracker:
    """Tracks latency milestones for a single conversational turn."""

    def __init__(self, session_id: str, turn_id: int = 1):
        self.session_id = session_id
        self.turn_id = turn_id
        self.milestones = LatencyMilestones()

    def mark(self, stage_name: str, timestamp: Optional[float] = None) -> float:
        """Record the timestamp for a named milestone."""
        ts = timestamp or time.perf_counter()
        if hasattr(self.milestones, stage_name):
            setattr(self.milestones, stage_name, ts)
        return ts

    def calculate(self) -> LatencyBreakdown:
        """Compute the breakdown in milliseconds."""
        m = self.milestones

        def diff(end: Optional[float], start: Optional[float]) -> Optional[float]:
            if end is not None and start is not None and end >= start:
                return round((end - start) * 1000.0, 2)
            return None

        vad_latency = diff(m.vad_detected, m.audio_received)
        stt_latency = diff(m.stt_completed, m.stt_started)
        llm_ttft = diff(m.first_token_received, m.llm_started)
        llm_total = diff(m.llm_completed, m.llm_started)
        tts_ttfa = diff(m.first_audio_received, m.tts_started)
        tts_total = diff(m.response_started, m.tts_started)

        # End to end: audio received to first response audio returned
        e2e_end = m.first_audio_received or m.response_started
        e2e = diff(e2e_end, m.audio_received)

        return LatencyBreakdown(
            vad_latency_ms=vad_latency,
            stt_latency_ms=stt_latency,
            llm_ttft_ms=llm_ttft,
            llm_total_ms=llm_total,
            tts_ttfa_ms=tts_ttfa,
            tts_total_ms=tts_total,
            end_to_end_ms=e2e,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert breakdown to dict for logging or metrics."""
        return self.calculate().model_dump()
