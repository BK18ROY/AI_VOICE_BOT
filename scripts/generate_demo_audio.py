"""Generate synthetic test WAV audio files for VAD and STT benchmarking."""

import os
import numpy as np
import soundfile as sf

OUTPUT_DIR = "data/audio"


def generate_speech_like_waveform(duration_s: float = 2.0, sample_rate: int = 16000) -> np.ndarray:
    """Generate a multi-harmonic waveform simulating vocal resonance."""
    num_samples = int(duration_s * sample_rate)
    t = np.linspace(0, duration_s, num_samples, endpoint=False)

    # Formant frequencies typical for human voice (F1=500Hz, F2=1500Hz, F3=2500Hz)
    f0 = 130.0  # Fundamental pitch
    sig = (
        0.4 * np.sin(2 * np.pi * f0 * t)
        + 0.25 * np.sin(2 * np.pi * 2 * f0 * t)
        + 0.15 * np.sin(2 * np.pi * 3 * f0 * t)
        + 0.1 * np.sin(2 * np.pi * 4 * f0 * t)
    )

    # Envelope modulation simulating syllables
    envelope = 0.5 * (1.0 + np.sin(2 * np.pi * 3.5 * t))
    voice = (sig * envelope).astype(np.float32)

    # Apply brief fade in and fade out
    fade_len = int(sample_rate * 0.05)
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)
    voice[:fade_len] *= fade_in
    voice[-fade_len:] *= fade_out

    return voice


def generate_silence(duration_s: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """Generate subtle background room noise / silence."""
    num_samples = int(duration_s * sample_rate)
    return (np.random.normal(0, 0.001, num_samples)).astype(np.float32)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sr = 16000

    # 1. Speech audio
    speech = generate_speech_like_waveform(duration_s=2.5, sample_rate=sr)
    sf.write(os.path.join(OUTPUT_DIR, "demo_speech.wav"), speech, sr, subtype="PCM_16")

    # 2. Silence audio
    silence = generate_silence(duration_s=1.5, sample_rate=sr)
    sf.write(os.path.join(OUTPUT_DIR, "demo_silence.wav"), silence, sr, subtype="PCM_16")

    # 3. Interrupted speech (silence -> speech -> brief silence -> speech)
    interrupted = np.concatenate([
        generate_silence(0.5, sr),
        generate_speech_like_waveform(1.2, sr),
        generate_silence(0.4, sr),
        generate_speech_like_waveform(1.5, sr),
    ])
    sf.write(os.path.join(OUTPUT_DIR, "demo_conversation_interrupted.wav"), interrupted, sr, subtype="PCM_16")

    print(f"[OK] Generated demo audio files in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
