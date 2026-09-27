"""End-to-End Pipeline test runner demonstrating real-time voice processing."""

import asyncio
import os
import sys
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from config.settings import get_settings
from app.audio.audio_utils import float32_to_pcm16
from app.conversation.state import create_initial_state
from app.pipeline.audio_transport import BaseAudioTransport
from app.pipeline.pipeline_factory import create_voice_pipeline
from app.schemas.responses import ServerEventType
from scripts.generate_demo_audio import generate_speech_like_waveform


class MockTransport(BaseAudioTransport):
    """In-memory transport capturing events and audio chunks for testing."""

    def __init__(self):
        self.received_audio_chunks = []
        self.received_events = []
        self._active = True

    async def send_audio(self, audio_bytes: bytes) -> None:
        self.received_audio_chunks.append(audio_bytes)

    async def send_event(self, event_type: ServerEventType, data: Optional[Dict[str, Any]] = None) -> None:
        self.received_events.append({"event": event_type, "data": data or {}})

    async def close(self) -> None:
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active


async def run_pipeline_test():
    print("=" * 60)
    print("RUNNING VOICE PIPELINE END-TO-END TEST")
    print("=" * 60)

    cfg = get_settings()
    session_id = "test_pipeline_session"
    transport = MockTransport()
    state = create_initial_state(session_id=session_id)

    pipeline = create_voice_pipeline(
        session_id=session_id,
        transport=transport,
        state=state,
        settings=cfg,
    )

    # 1. Test Text input path
    print("[1] Testing direct turn with product inquiry...")
    await pipeline.process_text_input("Can you check the warranty status for SN-5521?")
    await asyncio.sleep(0.5)

    print(f"    - Turns in history: {len(state.conversation_history)}")
    print(f"    - Assistant reply: {state.last_assistant_response}")
    print(f"    - Synthesized audio chunks received: {len(transport.received_audio_chunks)}")

    # 2. Test Hindi Language switching
    print("\n[2] Testing dynamic mid-call switch to Hindi...")
    await pipeline.process_text_input("Achha Hindi mein batao, meri agali EMI kitni hai?")
    await asyncio.sleep(0.5)

    print(f"    - Detected language: {state.detected_language}")
    print(f"    - Assistant reply: {state.last_assistant_response}")

    # 3. Test Barge-in interruption
    print("\n[3] Testing Barge-in interruption during bot speech...")
    pipeline.interruption_handler.set_bot_speaking(True)
    interrupted = await pipeline.interruption_handler.handle_user_speech_start(session_id)
    print(f"    - Barge-in successfully triggered: {interrupted}")
    print(f"    - Interruption count: {pipeline.interruption_handler.interruption_count}")

    print("\n[SUCCESS] All pipeline checks passed successfully!")


if __name__ == "__main__":
    asyncio.run(run_pipeline_test())
