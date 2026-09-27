"""Health, readiness, and metrics inspection endpoints."""

import time
from fastapi import APIRouter
from config.settings import get_settings
from app.observability.metrics import metrics_collector
from app.schemas.responses import HealthResponse, MetricsResponse, ReadyResponse

router = APIRouter(tags=["Monitoring & Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Liveness probe returning service status."""
    return HealthResponse(
        status="healthy",
        service="ai-voice-bot",
        timestamp=time.time(),
        version="1.0.0",
    )


@router.get("/ready", response_model=ReadyResponse)
async def get_readiness() -> ReadyResponse:
    """Readiness probe evaluating provider configuration."""
    cfg = get_settings()
    providers = {
        "stt": "mock" if cfg.enable_mock_stt else "deepspeech",
        "llm": "mock" if cfg.enable_mock_llm else f"gemini ({cfg.gemini_model})",
        "tts": "mock" if cfg.enable_mock_tts else f"cartesia ({cfg.cartesia_model})",
        "vad": "silero_compatible",
    }
    return ReadyResponse(
        status="ready",
        providers=providers,
        environment="mock" if (cfg.enable_mock_stt and cfg.enable_mock_llm and cfg.enable_mock_tts) else "production",
        details={
            "websocket_port": cfg.websocket_port,
            "vad_threshold": cfg.vad_threshold,
            "recordings_dir": cfg.recordings_dir,
        },
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """Prometheus/Dashboard-compatible real-time performance metrics."""
    return metrics_collector.get_metrics()
