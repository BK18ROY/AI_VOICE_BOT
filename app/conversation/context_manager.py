"""In-memory and persistent conversation session and context management."""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from app.observability.logger import logger
from app.schemas.conversation import ConversationState, ConversationTurn, LanguageCode, MessageRole
from app.schemas.responses import SessionSummary


class ContextManager:
    """Manages active conversation sessions, turn progression, and persistence."""

    def __init__(self, transcripts_dir: str = "outputs/transcripts"):
        self.transcripts_dir = transcripts_dir
        self._sessions: Dict[str, ConversationState] = {}
        self._session_start_times: Dict[str, float] = {}
        self._interruption_counters: Dict[str, int] = {}
        os.makedirs(self.transcripts_dir, exist_ok=True)

    def register_session(self, state: ConversationState) -> None:
        """Register a new conversation session."""
        self._sessions[state.session_id] = state
        self._session_start_times[state.session_id] = time.time()
        self._interruption_counters[state.session_id] = 0

    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """Fetch active session state."""
        return self._sessions.get(session_id)

    def record_interruption(self, session_id: str) -> None:
        """Increment interruption counter for a session."""
        if session_id in self._interruption_counters:
            self._interruption_counters[session_id] += 1
        state = self.get_session(session_id)
        if state:
            state.interruption_state = True

    def end_session(self, session_id: str) -> Optional[SessionSummary]:
        """Finalize conversation session and compile post-call analytics summary."""
        state = self._sessions.pop(session_id, None)
        start_time = self._session_start_times.pop(session_id, time.time())
        interruptions = self._interruption_counters.pop(session_id, 0)

        if not state:
            return None

        end_time = time.time()
        duration_s = round(end_time - start_time, 2)

        turn_latencies = [
            t.latency_ms for t in state.conversation_history if t.latency_ms is not None and t.latency_ms > 0
        ]
        avg_lat = float(np.mean(turn_latencies)) if turn_latencies else 0.0
        p95_lat = float(np.percentile(turn_latencies, 95)) if turn_latencies else 0.0
        total_lat = sum(turn_latencies)

        summary = SessionSummary(
            session_id=state.session_id,
            caller_id=state.caller_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_s,
            total_turns=len(state.conversation_history),
            interruption_count=interruptions,
            detected_language=state.detected_language,
            primary_intent=state.current_intent,
            active_workflow=state.active_workflow,
            provider_failures=state.metadata.get("provider_failures", {}),
            average_turn_latency_ms=round(avg_lat, 2),
            p95_turn_latency_ms=round(p95_lat, 2),
            total_latency_ms=round(total_lat, 2),
            history=state.conversation_history,
        )

        # Save transcript to disk
        self._save_transcript_to_file(summary)
        return summary

    def _save_transcript_to_file(self, summary: SessionSummary) -> None:
        """Persist session transcript and metadata as JSON."""
        try:
            filename = f"session_{summary.session_id}_{int(summary.start_time)}.json"
            filepath = Path(self.transcripts_dir) / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(summary.model_dump(), f, indent=2, ensure_ascii=False)
            logger.info("transcript_saved", path=str(filepath), session_id=summary.session_id)
        except Exception as e:
            logger.error("transcript_save_failed", session_id=summary.session_id, error=str(e))
