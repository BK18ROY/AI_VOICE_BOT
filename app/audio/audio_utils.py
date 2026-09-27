"""Audio utilities for format conversion, normalization, and validation."""

import io
from typing import Tuple
import numpy as np
import soundfile as sf


def pcm16_to_float32(pcm_bytes: bytes) -> np.ndarray:
    """Convert raw 16-bit linear PCM byte buffer to normalized float32 numpy array [-1.0, 1.0]."""
    if not pcm_bytes:
        return np.array([], dtype=np.float32)
    # 2 bytes per sample
    int16_data = np.frombuffer(pcm_bytes, dtype=np.int16)
    float32_data = int16_data.astype(np.float32) / 32768.0
    return float32_data


def float32_to_pcm16(float_array: np.ndarray) -> bytes:
    """Convert float32 numpy array [-1.0, 1.0] to raw 16-bit linear PCM byte buffer."""
    if float_array.size == 0:
        return b""
    clipped = np.clip(float_array, -1.0, 1.0)
    int16_data = (clipped * 32767.0).astype(np.int16)
    return int16_data.tobytes()


def to_mono(audio: np.ndarray) -> np.ndarray:
    """Ensure audio array is single-channel mono."""
    if audio.ndim == 1:
        return audio
    if audio.ndim == 2:
        return np.mean(audio, axis=1)
    raise ValueError(f"Unsupported audio dimension: {audio.ndim}")


def normalize_audio(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """Peak normalize audio array."""
    if audio.size == 0:
        return audio
    peak = np.max(np.abs(audio))
    if peak > 0:
        return audio * (target_peak / peak)
    return audio


def calculate_duration(audio_bytes: bytes, sample_rate: int = 16000, bytes_per_sample: int = 2) -> float:
    """Calculate audio duration in seconds from raw PCM byte length."""
    num_samples = len(audio_bytes) // bytes_per_sample
    return num_samples / float(sample_rate)


def validate_pcm_chunk(chunk_bytes: bytes, max_bytes: int = 65536) -> bool:
    """Validate incoming PCM chunk for reasonable size and even byte alignment."""
    if not chunk_bytes:
        return False
    if len(chunk_bytes) % 2 != 0:
        # PCM16 requires 2-byte alignment
        return False
    if len(chunk_bytes) > max_bytes:
        return False
    return True


def create_wav_bytes(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Wrap raw PCM16 bytes in a standard RIFF/WAV header."""
    float_data = pcm16_to_float32(pcm_bytes)
    out_buffer = io.BytesIO()
    sf.write(out_buffer, float_data, samplerate=sample_rate, format='WAV', subtype='PCM_16')
    return out_buffer.getvalue()


def read_wav_bytes(wav_bytes: bytes) -> Tuple[np.ndarray, int]:
    """Read a WAV byte stream into a float32 array and return (data, sample_rate)."""
    in_buffer = io.BytesIO(wav_bytes)
    data, sample_rate = sf.read(in_buffer, dtype='float32')
    return to_mono(data), sample_rate
