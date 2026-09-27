"""Factory for creating production or mock Voice Pipelines."""

from typing import Optional
from config.settings import Settings, get_settings
from app.conversation.graph import ConversationWorkflowGraph
from app.pipeline.audio_transport import BaseAudioTransport
from app.pipeline.interruption_handler import InterruptionHandler
from app.pipeline.llm_processor import LLMProcessor
from app.pipeline.stt_processor import STTProcessor
from app.pipeline.tts_processor import TTSProcessor
from app.pipeline.vad_processor import VADProcessor
from app.pipeline.voice_pipeline import VoicePipeline
from app.providers.llm.gemini_provider import GeminiProvider
from app.providers.llm.mock_llm import MockLLMProvider
from app.providers.stt.deepspeech_provider import DeepSpeechProvider
from app.providers.stt.mock_stt import MockSTTProvider
from app.providers.tts.cartesia_provider import CartesiaTTSProvider
from app.providers.tts.mock_tts import MockTTSProvider
from app.schemas.conversation import ConversationState


def create_voice_pipeline(
    session_id: str,
    transport: BaseAudioTransport,
    state: ConversationState,
    settings: Optional[Settings] = None,
) -> VoicePipeline:
    """Instantiate a VoicePipeline configured according to current environment settings."""
    cfg = settings or get_settings()

    # 1. STT Engine
    if cfg.enable_mock_stt:
        stt_engine = MockSTTProvider()
    else:
        stt_engine = DeepSpeechProvider(
            model_path=cfg.deepspeech_model_path,
            scorer_path=cfg.deepspeech_scorer_path,
        )
    stt_proc = STTProcessor(provider=stt_engine, timeout_seconds=cfg.stt_timeout_seconds)

    # 2. LLM Engine & LangGraph
    workflow_graph = ConversationWorkflowGraph()
    if cfg.enable_mock_llm:
        llm_engine = GeminiProvider(api_key=None)  # Automatically routes to MockLLM
    else:
        llm_engine = GeminiProvider(
            api_key=cfg.gemini_api_key,
            model_name=cfg.gemini_model,
            project_id=cfg.google_cloud_project,
            location=cfg.google_cloud_location,
            timeout_seconds=cfg.llm_timeout_seconds,
        )
    llm_proc = LLMProcessor(
        workflow_graph=workflow_graph,
        llm_provider=llm_engine,
        timeout_seconds=cfg.llm_timeout_seconds,
    )

    # 3. TTS Engine
    if cfg.enable_mock_tts:
        tts_engine = MockTTSProvider(sample_rate=cfg.vad_sample_rate)
    else:
        tts_engine = CartesiaTTSProvider(
            api_key=cfg.cartesia_api_key,
            voice_id=cfg.cartesia_voice_id,
            model=cfg.cartesia_model,
            sample_rate=cfg.vad_sample_rate,
            timeout_seconds=cfg.tts_timeout_seconds,
        )
    tts_proc = TTSProcessor(provider=tts_engine, timeout_seconds=cfg.tts_timeout_seconds)

    # 4. VAD & Interruption Handler
    interruption_handler = InterruptionHandler()
    vad_proc = VADProcessor(
        threshold=cfg.vad_threshold,
        min_speech_duration_s=cfg.vad_min_speech_duration,
        min_silence_duration_s=cfg.vad_min_silence_duration,
        sample_rate=cfg.vad_sample_rate,
    )

    return VoicePipeline(
        session_id=session_id,
        transport=transport,
        vad=vad_proc,
        stt=stt_proc,
        llm=llm_proc,
        tts=tts_proc,
        state=state,
        interruption_handler=interruption_handler,
    )
