"""Audio stream chunking and packetization."""

import os
import time
from pathlib import Path
from typing import Generator, List, Optional
from app.schemas.audio import AudioChunk, AudioFormat
from app.audio.audio_utils import create_wav_bytes


class AudioChunker:
    """Slices raw audio bytes into fixed-duration frames and generates unique chunk metadata."""

    def __init__(
        self,
        session_id: str,
        sample_rate: int = 16000,
        chunk_duration_ms: float = 20.0,
        channels: int = 1,
    ):
        self.session_id = session_id
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.channels = channels
        # Calculate bytes per chunk: (sample_rate * channels * 2 bytes * duration_ms / 1000)
        self.bytes_per_sample = 2 * channels
        self.chunk_size_bytes = int((sample_rate * chunk_duration_ms / 1000.0) * self.bytes_per_sample)
        self.sequence_number = 0
        self._residual_buffer = bytearray()

    def process_incoming_bytes(self, data: bytes) -> List[AudioChunk]:
        """Buffer incoming bytes and return ready fixed-size AudioChunk objects."""
        self._residual_buffer.extend(data)
        ready_chunks: List[AudioChunk] = []

        while len(self._residual_buffer) >= self.chunk_size_bytes:
            chunk_data = bytes(self._residual_buffer[: self.chunk_size_bytes])
            del self._residual_buffer[: self.chunk_size_bytes]

            self.sequence_number += 1
            now = time.time()
            chunk = AudioChunk(
                session_id=self.session_id,
                sequence_number=self.sequence_number,
                timestamp=now,
                sample_rate=self.sample_rate,
                channels=self.channels,
                format=AudioFormat.PCM16,
                duration_ms=self.chunk_duration_ms,
                raw_bytes=chunk_data,
            )
            ready_chunks.append(chunk)

        return ready_chunks

    def flush(self) -> Optional[AudioChunk]:
        """Flush remaining buffered bytes if any."""
        if not self._residual_buffer:
            return None

        chunk_data = bytes(self._residual_buffer)
        self._residual_buffer.clear()
        self.sequence_number += 1
        now = time.time()
        duration_ms = (len(chunk_data) / float(self.bytes_per_sample * self.sample_rate)) * 1000.0

        return AudioChunk(
            session_id=self.session_id,
            sequence_number=self.sequence_number,
            timestamp=now,
            sample_rate=self.sample_rate,
            channels=self.channels,
            format=AudioFormat.PCM16,
            duration_ms=duration_ms,
            raw_bytes=chunk_data,
        )

    def save_chunk_to_wav(self, chunk: AudioChunk, output_dir: str) -> Path:
        """Persist chunk to disk with unique collision-free naming."""
        os.makedirs(output_dir, exist_ok=True)
        # Unique identifier requirement: {session_id}_{sequence_number}_{timestamp}.wav
        filename = f"{chunk.get_chunk_id()}.wav"
        file_path = Path(output_dir) / filename

        # Ensure no accidental overwriting
        counter = 1
        while file_path.exists():
            file_path = Path(output_dir) / f"{chunk.get_chunk_id()}_{counter}.wav"
            counter += 1

        wav_data = create_wav_bytes(chunk.raw_bytes, sample_rate=chunk.sample_rate, channels=chunk.channels)
        with open(file_path, "wb") as f:
            f.write(wav_data)

        return file_path
