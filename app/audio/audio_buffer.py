"""Thread-safe circular and streaming speech audio buffer."""

import asyncio
from collections import deque
from typing import List, Optional
from app.schemas.audio import AudioChunk


class AudioRingBuffer:
    """Ring buffer maintaining recent audio frames (pre-roll buffer) and active utterance data."""

    def __init__(self, max_pre_roll_chunks: int = 15):
        # 15 chunks * 20ms = ~300ms pre-roll audio to catch start of speech
        self.max_pre_roll_chunks = max_pre_roll_chunks
        self._pre_roll: deque[AudioChunk] = deque(maxlen=max_pre_roll_chunks)
        self._active_utterance: List[AudioChunk] = []
        self._is_recording_speech = False
        self._lock = asyncio.Lock()

    async def add_chunk(self, chunk: AudioChunk) -> None:
        """Add an incoming audio chunk to the buffer."""
        async with self._lock:
            if not self._is_recording_speech:
                self._pre_roll.append(chunk)
            else:
                self._active_utterance.append(chunk)

    async def start_utterance(self) -> None:
        """Called when VAD triggers speech start. Moves pre-roll into active utterance."""
        async with self._lock:
            self._is_recording_speech = True
            self._active_utterance.clear()
            self._active_utterance.extend(self._pre_roll)
            self._pre_roll.clear()

    async def end_utterance(self) -> bytes:
        """Called when VAD triggers speech end. Returns combined PCM bytes of the utterance."""
        async with self._lock:
            self._is_recording_speech = False
            raw_pcm = b"".join(c.raw_bytes for c in self._active_utterance)
            self._active_utterance.clear()
            return raw_pcm

    async def clear(self) -> None:
        """Flush and drop all buffered audio (critical during barge-in/interruption)."""
        async with self._lock:
            self._is_recording_speech = False
            self._pre_roll.clear()
            self._active_utterance.clear()

    @property
    def is_recording(self) -> bool:
        return self._is_recording_speech
