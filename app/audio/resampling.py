"""Audio resampling utilities."""

import numpy as np


def resample_linear(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample 1D float32 audio using high-speed linear interpolation."""
    if orig_sr == target_sr or audio.size == 0:
        return audio

    orig_length = len(audio)
    target_length = int(np.round(orig_length * float(target_sr) / float(orig_sr)))

    orig_indices = np.linspace(0, orig_length - 1, num=orig_length)
    target_indices = np.linspace(0, orig_length - 1, num=target_length)

    resampled = np.interp(target_indices, orig_indices, audio).astype(np.float32)
    return resampled


def resample_pcm16(pcm_bytes: bytes, orig_sr: int, target_sr: int) -> bytes:
    """Resample raw PCM16 bytes directly from orig_sr to target_sr."""
    if orig_sr == target_sr or not pcm_bytes:
        return pcm_bytes

    from app.audio.audio_utils import pcm16_to_float32, float32_to_pcm16
    float_data = pcm16_to_float32(pcm_bytes)
    resampled_float = resample_linear(float_data, orig_sr, target_sr)
    return float32_to_pcm16(resampled_float)
