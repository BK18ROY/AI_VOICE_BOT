"""Centralized application settings using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema and environment variable parser."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Google Cloud & Gemini Configuration
    google_cloud_project: Optional[str] = Field(
        default=None,
        description="GCP Project ID for Vertex AI or Google GenAI integration",
    )
    google_cloud_location: str = Field(
        default="us-central1",
        description="Vertex AI region",
    )
    google_application_credentials: Optional[str] = Field(
        default=None,
        description="Path to GCP Service Account JSON key",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini LLM model identifier",
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google AI Studio Gemini API key",
    )

    # Cartesia TTS Configuration
    cartesia_api_key: Optional[str] = Field(
        default=None,
        description="Cartesia TTS API key",
    )
    cartesia_voice_id: str = Field(
        default="a0e99841-438c-4a64-b679-ae501e7d6091",
        description="Cartesia Voice ID (e.g. Sonic multilingual / conversational)",
    )
    cartesia_model: str = Field(
        default="sonic-multilingual",
        description="Cartesia TTS model name",
    )

    # DeepSpeech / STT Configuration
    deepspeech_model_path: Optional[str] = Field(
        default=None,
        description="Path to DeepSpeech .pbmm model file",
    )
    deepspeech_scorer_path: Optional[str] = Field(
        default=None,
        description="Path to DeepSpeech .scorer file",
    )

    # Network & Transport
    websocket_host: str = Field(
        default="0.0.0.0",
        description="Host to bind FastAPI WebSocket server",
    )
    websocket_port: int = Field(
        default=8000,
        description="Port for FastAPI WebSocket server",
    )

    # Voice Activity Detection (VAD)
    vad_threshold: float = Field(
        default=0.5,
        description="Silero VAD speech probability threshold (0.0 to 1.0)",
    )
    vad_min_speech_duration: float = Field(
        default=0.25,
        description="Minimum speech duration in seconds to trigger speech_start",
    )
    vad_min_silence_duration: float = Field(
        default=0.5,
        description="Silence duration in seconds before considering speech ended",
    )
    vad_sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz expected by VAD and STT pipeline",
    )

    # Observability & Logging
    log_level: str = Field(
        default="INFO",
        description="Application log level: DEBUG, INFO, WARNING, ERROR",
    )
    enable_structured_logs: bool = Field(
        default=True,
        description="Whether to format logs as structured JSON / key-value logs",
    )

    # Mock Mode Provider Flags (Default True to run without external dependencies)
    enable_mock_stt: bool = Field(
        default=True,
        description="Use deterministic Mock STT provider instead of DeepSpeech",
    )
    enable_mock_llm: bool = Field(
        default=True,
        description="Use Mock Gemini LLM provider instead of live Vertex/Gemini API",
    )
    enable_mock_tts: bool = Field(
        default=True,
        description="Use Mock Cartesia TTS provider instead of live Cartesia API",
    )

    # Telephony & Post-Call Storage Directories
    recordings_dir: str = Field(default="outputs/audio")
    transcripts_dir: str = Field(default="outputs/transcripts")
    metrics_dir: str = Field(default="outputs/metrics")
    reports_dir: str = Field(default="outputs/reports")
    enable_post_call_analysis: bool = Field(
        default=True,
        description="Save transcripts and latency reports automatically after call",
    )

    # RabbitMQ / Async Queue
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL for async worker jobs",
    )
    enable_async_queue: bool = Field(
        default=False,
        description="Whether to dispatch background post-call events to RabbitMQ",
    )

    # Pipeline limits & timeouts
    stt_timeout_seconds: float = Field(default=3.0)
    llm_timeout_seconds: float = Field(default=5.0)
    tts_timeout_seconds: float = Field(default=4.0)
    max_retries: int = Field(default=2)
    max_audio_chunk_bytes: int = Field(default=65536)  # 64KB per websocket message


@lru_cache()
def get_settings() -> Settings:
    """Return cached instance of Settings."""
    return Settings()
