# Conversational Voice AI Platform — System Architecture

This document details the architectural design, telephony integration, streaming data flow, state management, and orchestration mechanics of the real-time Conversational Voice AI platform.

---

## 1. Architectural Topology Overview

The platform is designed to handle high-concurrency, low-latency, bidirectional conversational audio over telephony gateways and WebSocket connections.

```
Caller (Phone / Mobile / Web Browser)
    │
    ▼
Telephony Network (PSTN / SIP Trunk)
    │
    ▼
Telephony Gateway (Asterisk PBX / FreeSWITCH / Twilio Media Streams)
    │
    ▼  [AudioSocket / Bidirectional WebSocket / 16kHz PCM16]
FastAPI Audio Streaming Layer (`/ws/voice`)
    │
    ▼
Pipecat-Inspired Streaming Pipeline
    ├── 1. Audio Ingestion & Frame Normalization (20ms frames)
    ├── 2. Silero-Compatible Voice Activity Detection (VAD)
    ├── 3. Speech Segmentation & Buffer Management
    ├── 4. DeepSpeech-Compatible Speech-To-Text (STT)
    ├── 5. Language Detection & Dynamic Mid-Call Switching (EN ↔ HI ↔ Hinglish)
    ├── 6. Conversation State & Context Memory Manager
    ├── 7. LangGraph Stateful Workflow Routing Machine
    ├── 8. Gemini 2.5 Flash Real-Time Generative LLM
    ├── 9. Domain Business Tools (Product, Finance, Roadside, Dealer)
    ├── 10. Cartesia Sonic Streaming Text-To-Speech (TTS)
    ├── 11. Barge-in / Interruption Cancellation Monitor
    └── 12. Asynchronous Audio Chunking & Output Dispatcher
    │
    ▼  [Low-latency Downstream PCM Audio]
Telephony Gateway / Caller Earpiece
```

---

## 2. Core Architectural Components

### 2.1 Telephony Ingestion & Transport Layer
- **Telephony Ingestion**: Integrates with PBX systems via **Asterisk AudioSocket** or **Twilio / LiveKit WebSocket Media Streams**.
- **Audio Format**: Normalized to **16,000 Hz, 16-bit Linear PCM, Single-Channel Mono**. Audio packets arrive in 20ms slices (640 bytes per chunk).
- **Audio Transport (`app/pipeline/audio_transport.py`)**: Abstract transport layer decouple pipeline mechanics from network protocols. WebSocket implementation (`WebSocketAudioTransport`) manages binary audio multiplexing with control JSON signals.

### 2.2 Voice Activity Detection (VAD)
- **Module (`app/pipeline/vad_processor.py`)**: Evaluates frame-level energy, RMS power, and spectral presence against configurable thresholds (`vad_threshold: 0.5`).
- **Timing Windows**:
  - `vad_min_speech_duration` (default 250ms): Filters spurious acoustic clicks, coughs, and microphone noise.
  - `vad_min_silence_duration` (default 500ms): Determines natural pause boundaries marking end-of-turn utterance completion.
- **State Machine**: Transitions across `SILENCE` ↔ `SPEECH_START` ↔ `SPEECH_ACTIVE` ↔ `SPEECH_END`.

### 2.3 Speech-to-Text (STT) Engine
- **Interface (`app/providers/stt/base.py`)**: Standardized base class supporting both batch chunking and continuous token/character streaming.
- **DeepSpeech Provider (`app/providers/stt/deepspeech_provider.py`)**: Local acoustic model evaluation using TensorFlow/DeepSpeech acoustic graphs with language model scorers.
- **Mock STT Provider (`app/providers/stt/mock_stt.py`)**: Deterministic local engine allowing full repository execution without multi-gigabyte model downloads or GPU hardware.

### 2.4 Language Detection & Code-Switching Engine
- **Module (`app/conversation/language_detector.py`)**:
  - Analyzes lexical tokens, regex directives, and Unicode code points.
  - Devanagari script range (`\u0900-\u097F`) detection for formal Hindi (`hi`).
  - Romanized dictionary heuristic scoring for Hinglish (`hinglish`).
  - Real-time mid-dialogue directive detection (e.g., *"Achha Hindi mein bolo"*, *"Please switch to English"*).

### 2.5 LangGraph State Machine & Workflow Routing
- **Module (`app/conversation/graph.py`)**:
  - Built on `langgraph.graph.StateGraph`.
  - Maintains conversation turns, intent classifications, active tools, and context across nodes:
    `receive_user_input` ➔ `detect_language` ➔ `context_retrieval` ➔ (conditional branch) ➔ `classify_intent` ➔ `workflow_router` ➔ `execute_business_tools` ➔ `generate_response` ➔ `prepare_tts`.
  - Conditional edge routing checks if the utterance is a follow-up to an ongoing business flow or a new domain inquiry.

### 2.6 Gemini 2.5 Flash Generative LLM
- **Module (`app/providers/llm/gemini_provider.py`)**:
  - Leverages Google Gemini 2.5 Flash for sub-100ms Time-To-First-Token (TTFT).
  - Streams tokens asynchronously via Server-Sent Events (SSE) or WebSocket streaming.
  - Incorporates circuit breakers (`app/recovery/circuit_breaker.py`) and automatic fallbacks to deterministic mock generators in offline or failure conditions.

### 2.7 Business Domain Tool Execution
- **Modules (`app/tools/*.py`)**:
  - **Product Support**: Serial number warranty status, stock availability lookup, order shipment tracking.
  - **Finance Support**: EMI calculation, loan balance inquiries, payment schedule queries.
  - **Roadside Assistance**: GPS location tracking, vehicle breakdown triage, towing patrol dispatch.
  - **Dealer Support**: Job card inspection status, nearest workshop finder, service manager routing.

### 2.8 Cartesia Sonic Streaming TTS
- **Module (`app/providers/tts/cartesia_provider.py`)**:
  - High-fidelity generative voice synthesis with ultra-low Time-To-First-Audio (TTFA).
  - Streaming chunk generation: converts token phrases into PCM16 chunks as soon as punctuation boundaries (comma, period, question mark) or 15+ characters arrive.
  - Mid-call cancellation mechanism for instant response to user interruptions.

### 2.9 Barge-In & Interruption Cancellation Handler
- **Module (`app/pipeline/interruption_handler.py`)**:
  - Listens concurrently for incoming voice frames while the assistant is streaming synthesized speech.
  - Upon VAD `SPEECH_START` event, immediately cancels the active asyncio TTS task, flushes transport output queues, and transmits an interruption control event to the client.

### 2.10 Observability, Metrics & Latency Profiling
- **Modules (`app/observability/*.py`)**:
  - **Latency Tracker**: Records exact timestamp milestones across VAD, STT, LLM TTFT, LLM Total, TTS TTFA, and End-to-End caller response.
  - **Metrics Collector**: In-memory thread-safe collector exposing p50, p90, p95, p99 latency percentiles and error counters for Prometheus/Grafana scrapers.
  - **Structured Logging**: JSON-formatted logging via `structlog` with session correlation IDs.
