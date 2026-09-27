"""Main application entry point for AI Voice Bot / Conversational AI Platform.

Provides both the FastAPI web application (HTTP REST & WebSocket streaming)
and the unified Command Line Interface (CLI).

Commands:
    python main.py server    - Launch production / mock FastAPI & WebSocket server
    python main.py demo      - Run interactive or scripted conversational simulation
    python main.py benchmark - Run real-time latency percentile benchmarking
    python main.py test      - Run automated pytest test suite
    python main.py health    - Check system health and provider readiness
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from config.settings import get_settings

# ==============================================================================
# FastAPI Application Construction
# ==============================================================================

settings = get_settings()

app = FastAPI(
    title="AI Voice Bot / Conversational AI Platform",
    description=(
        "Production-style real-time generative AI conversational voice assistant "
        "featuring Gemini 2.5 Flash, Cartesia TTS, Silero VAD, and LangGraph workflow orchestration."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API and WebSocket routers
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root_info() -> Dict[str, Any]:
    """Root metadata and platform overview."""
    cfg = get_settings()
    return {
        "service": "ai-voice-bot",
        "version": "1.0.0",
        "description": "Real-Time Conversational AI Voice Platform",
        "endpoints": {
            "health": "/health",
            "readiness": "/ready",
            "metrics": "/metrics",
            "websocket_voice": "/ws/voice",
            "docs": "/docs",
        },
        "mode": "mock" if (cfg.enable_mock_stt and cfg.enable_mock_llm and cfg.enable_mock_tts) else "production",
        "providers": {
            "stt": "mock" if cfg.enable_mock_stt else "deepspeech",
            "llm": "mock" if cfg.enable_mock_llm else f"gemini ({cfg.gemini_model})",
            "tts": "mock" if cfg.enable_mock_tts else f"cartesia ({cfg.cartesia_model})",
        },
    }


# ==============================================================================
# CLI Commands Implementation
# ==============================================================================

def run_server_command(host: str, port: int, reload: bool) -> None:
    """Launch uvicorn server."""
    print(f"[*] Starting AI Voice Bot server on {host}:{port} (reload={reload})...")
    uvicorn.run("main:app", host=host, port=port, reload=reload, log_level="info")


async def run_demo_async(scenario_file: Optional[str] = None) -> None:
    """Run an end-to-end multi-turn simulated conversation through the pipeline."""
    from app.conversation.state import create_initial_state
    from app.pipeline.audio_transport import BaseAudioTransport
    from app.pipeline.pipeline_factory import create_voice_pipeline
    from app.schemas.responses import ServerEventType

    print("\n" + "=" * 65)
    print("AI VOICE BOT - REAL-TIME CONVERSATIONAL DEMO")
    print("=" * 65)

    cfg = get_settings()

    # Determine dialogue scenario
    if scenario_file and os.path.exists(scenario_file):
        with open(scenario_file, "r", encoding="utf-8") as f:
            demo_spec = json.load(f)
    else:
        # Default fallback to demo_multilingual_switch.json if available
        default_scenario = Path("data/demo/demo_multilingual_switch.json")
        if default_scenario.exists():
            with open(default_scenario, "r", encoding="utf-8") as f:
                demo_spec = json.load(f)
        else:
            demo_spec = {
                "scenario": "Customer Support Inquiries",
                "caller_id": "caller_demo_user",
                "turns": [
                    {"turn": 1, "user": "Hello, can you check the warranty status for SN-5521?"},
                    {"turn": 2, "user": "Achha Hindi mein batao meri EMI ka status kya hai account ACC-101 ke liye?"},
                    {"turn": 3, "user": "My car broke down on Highway 48 near mile marker 24, need roadside help!"},
                    {"turn": 4, "user": "Where is the nearest authorized dealer in north zone?"},
                ]
            }

    print(f"[*] Scenario : {demo_spec.get('scenario', 'Interactive Simulation')}")
    print(f"[*] Caller ID: {demo_spec.get('caller_id', 'demo_caller')}")
    print(f"[*] Mock Mode: {cfg.enable_mock_stt}\n" + "-" * 65)

    # In-memory transport tracking synthesized audio
    class DemoAudioTransport(BaseAudioTransport):
        def __init__(self):
            self.audio_chunks = []
            self.events = []
            self.last_tts_complete = None

        async def send_audio(self, audio_bytes: bytes) -> None:
            self.audio_chunks.append(audio_bytes)

        async def send_event(self, event_type: ServerEventType, data: Optional[Dict[str, Any]] = None) -> None:
            self.events.append((event_type, data))
            if event_type == ServerEventType.TTS_COMPLETE:
                self.last_tts_complete = data

        async def close(self) -> None:
            pass

        @property
        def is_active(self) -> bool:
            return True

    session_id = f"demo_sess_{os.getpid()}"
    transport = DemoAudioTransport()
    state = create_initial_state(session_id=session_id, caller_id=demo_spec.get("caller_id", "demo_caller"))
    pipeline = create_voice_pipeline(session_id=session_id, transport=transport, state=state, settings=cfg)

    turns = demo_spec.get("turns", [])
    for idx, t in enumerate(turns, start=1):
        user_text = t.get("user")
        print(f"\n[Turn {idx:02d}] 🗣️  Caller:")
        print(f"         \"{user_text}\"")

        transport.audio_chunks.clear()
        transport.last_tts_complete = None

        # Execute turn
        await pipeline.process_text_input(user_text)
        await asyncio.sleep(0.05)

        # Inspect generated response from conversation state
        bot_reply = state.last_assistant_response or "(No reply)"
        lang = state.detected_language.value if hasattr(state.detected_language, "value") else str(state.detected_language)
        intent = state.current_intent.value if (state.current_intent and hasattr(state.current_intent, "value")) else str(state.current_intent)

        print(f"        🤖 Bot [{lang} | {intent}]:")
        print(f"         \"{bot_reply}\"")

        audio_size = sum(len(c) for c in transport.audio_chunks)
        print(f"        🔊 Audio Output: {len(transport.audio_chunks)} chunks synthesized ({audio_size} bytes PCM)")

        if transport.last_tts_complete:
            lat = transport.last_tts_complete.get("latency_breakdown", {})
            e2e = lat.get("end_to_end_ms", 0.0)
            llm_ttft = lat.get("llm_ttft_ms", 0.0)
            tts_ttfa = lat.get("tts_ttfa_ms", 0.0)
            print(f"        ⏱️  Latencies   : E2E = {e2e:.1f}ms | LLM TTFT = {llm_ttft:.1f}ms | TTS TTFA = {tts_ttfa:.1f}ms")

    print("\n" + "=" * 65)
    print("✅ Demo session finished successfully!")
    print(f"[*] Total turns completed: {len(state.conversation_history)}")
    print("=" * 65 + "\n")


def run_benchmark_command(runs: int) -> None:
    """Run real-time latency benchmark."""
    from scripts.benchmark_latency import run_benchmark
    asyncio.run(run_benchmark(num_runs=runs))


def run_tests_command(pytest_args: Optional[str] = None) -> None:
    """Invoke pytest test suite."""
    import pytest
    args = pytest_args.split() if pytest_args else ["-v", "tests"]
    print(f"[*] Executing pytest with args: {args}...")
    exit_code = pytest.main(args)
    if exit_code == 0:
        print("[*] All tests passed!")
    else:
        print(f"[!] Pytest completed with exit code: {exit_code}")
        sys.exit(exit_code)


def run_health_command() -> None:
    """Inspect environment configuration and provider readiness."""
    cfg = get_settings()
    print("\n" + "=" * 65)
    print("AI VOICE BOT - SYSTEM HEALTH & READINESS PROBE")
    print("=" * 65)
    print(f"{'Parameter':<32} | {'Value'}")
    print("-" * 65)
    print(f"{'Service Name':<32} | ai-voice-bot")
    print(f"{'Version':<32} | 1.0.0")
    print(f"{'WebSocket Server Host':<32} | {cfg.websocket_host}:{cfg.websocket_port}")
    print(f"{'VAD Sample Rate':<32} | {cfg.vad_sample_rate} Hz")
    print(f"{'VAD Threshold':<32} | {cfg.vad_threshold}")
    print(f"{'Mock STT Mode':<32} | {cfg.enable_mock_stt}")
    print(f"{'Mock LLM Mode':<32} | {cfg.enable_mock_llm}")
    print(f"{'Mock TTS Mode':<32} | {cfg.enable_mock_tts}")
    print(f"{'Gemini Model':<32} | {cfg.gemini_model}")
    print(f"{'Cartesia Model':<32} | {cfg.cartesia_model}")
    print(f"{'Recordings Directory':<32} | {cfg.recordings_dir}")
    print(f"{'Transcripts Directory':<32} | {cfg.transcripts_dir}")
    print(f"{'Metrics Directory':<32} | {cfg.metrics_dir}")
    print("-" * 65)

    mode = "MOCK (Zero external credentials required)" if (
        cfg.enable_mock_stt and cfg.enable_mock_llm and cfg.enable_mock_tts
    ) else "PRODUCTION (Live Cloud Providers Active)"

    print(f"Current Operating Mode: {mode}")
    print("=" * 65 + "\n")


# ==============================================================================
# CLI Entrypoint Dispatcher
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="voice-bot",
        description="AI Voice Bot - Real-time Conversational Voice AI Platform",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: server
    server_parser = subparsers.add_parser("server", help="Start FastAPI & WebSocket server")
    server_parser.add_argument("--host", default=settings.websocket_host, help="Bind host")
    server_parser.add_argument("--port", type=int, default=settings.websocket_port, help="Bind port")
    server_parser.add_argument("--reload", action="store_true", help="Enable code auto-reload")

    # Command: demo
    demo_parser = subparsers.add_parser("demo", help="Run local conversation simulation")
    demo_parser.add_argument("--scenario", default=None, help="Path to custom JSON demo conversation scenario")

    # Command: benchmark
    bench_parser = subparsers.add_parser("benchmark", help="Execute real-time latency percentiles benchmark")
    bench_parser.add_argument("--runs", type=int, default=20, help="Number of benchmark iterations")

    # Command: test
    test_parser = subparsers.add_parser("test", help="Execute automated test suite with pytest")
    test_parser.add_argument("--args", default="-v tests", help="Arguments to forward to pytest")

    # Command: health
    subparsers.add_parser("health", help="Check system health, readiness, and provider config")

    args = parser.parse_args()

    if args.command == "server":
        run_server_command(host=args.host, port=args.port, reload=args.reload)
    elif args.command == "demo":
        asyncio.run(run_demo_async(scenario_file=args.scenario))
    elif args.command == "benchmark":
        run_benchmark_command(runs=args.runs)
    elif args.command == "test":
        run_tests_command(pytest_args=args.args)
    elif args.command == "health":
        run_health_command()
    else:
        parser.print_help()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
