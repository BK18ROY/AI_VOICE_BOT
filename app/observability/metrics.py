"""In-memory thread-safe metrics collector."""

import threading
import numpy as np
from typing import Dict, List, Optional
from app.schemas.responses import MetricsResponse


class MetricsCollector:
    """Thread-safe collector for real-time system metrics."""

    def __init__(self):
        self._lock = threading.Lock()
        self.active_sessions: int = 0
        self.total_sessions: int = 0
        self.successful_sessions: int = 0
        self.failed_sessions: int = 0
        self.barge_in_count: int = 0
        self.stt_failures: int = 0
        self.llm_failures: int = 0
        self.tts_failures: int = 0
        self._latencies_ms: List[float] = []

    def session_started(self) -> None:
        with self._lock:
            self.active_sessions += 1
            self.total_sessions += 1

    def session_completed(self, success: bool = True) -> None:
        with self._lock:
            if self.active_sessions > 0:
                self.active_sessions -= 1
            if success:
                self.successful_sessions += 1
            else:
                self.failed_sessions += 1

    def record_turn_latency(self, latency_ms: Optional[float]) -> None:
        if latency_ms is None or latency_ms <= 0:
            return
        with self._lock:
            self._latencies_ms.append(latency_ms)
            # Cap array size to avoid infinite memory growth
            if len(self._latencies_ms) > 10000:
                self._latencies_ms = self._latencies_ms[-5000:]

    def record_barge_in(self) -> None:
        with self._lock:
            self.barge_in_count += 1

    def record_failure(self, component: str) -> None:
        with self._lock:
            comp = component.lower()
            if "stt" in comp:
                self.stt_failures += 1
            elif "llm" in comp:
                self.llm_failures += 1
            elif "tts" in comp:
                self.tts_failures += 1

    def get_metrics(self) -> MetricsResponse:
        with self._lock:
            lats = self._latencies_ms
            avg_lat = float(np.mean(lats)) if lats else 0.0
            p95_lat = float(np.percentile(lats, 95)) if lats else 0.0

            return MetricsResponse(
                active_sessions=self.active_sessions,
                total_sessions=self.total_sessions,
                successful_sessions=self.successful_sessions,
                failed_sessions=self.failed_sessions,
                average_latency_ms=round(avg_lat, 2),
                p95_latency_ms=round(p95_lat, 2),
                barge_in_count=self.barge_in_count,
                stt_failures=self.stt_failures,
                llm_failures=self.llm_failures,
                tts_failures=self.tts_failures,
            )

    def reset(self) -> None:
        with self._lock:
            self.active_sessions = 0
            self.total_sessions = 0
            self.successful_sessions = 0
            self.failed_sessions = 0
            self.barge_in_count = 0
            self.stt_failures = 0
            self.llm_failures = 0
            self.tts_failures = 0
            self._latencies_ms.clear()


# Global singleton instance
metrics_collector = MetricsCollector()
