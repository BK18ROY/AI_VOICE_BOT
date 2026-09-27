"""Speech-to-Text providers package."""

from app.providers.stt.base import BaseSTTProvider, STTResult
from app.providers.stt.deepspeech_provider import DeepSpeechProvider
from app.providers.stt.mock_stt import MockSTTProvider

__all__ = ["BaseSTTProvider", "STTResult", "DeepSpeechProvider", "MockSTTProvider"]
