# Conversational Voice AI Platform — Deployment & Production Guide

This guide covers deployment strategies, environment configurations, Docker operations, and telephony gateway integration.

---

## 1. Local Environment Setup

### Prerequisites
- Python 3.10, 3.11, or 3.12
- `git`
- Port `8000` available for HTTP/WebSocket traffic

### Installation
```bash
# 1. Clone repository
git clone https://github.com/example/ai-voice-bot.git
cd ai-voice-bot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# 3. Install core dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env
```

---

## 2. Running with Docker & Docker Compose

The repository includes a multi-stage production Docker setup with health checks.

### Run with Docker Compose
```bash
# Start voice bot server in mock mode (default, no API keys required)
docker compose up -d

# Check service logs
docker compose logs -f voice-bot

# Check container health status
docker compose ps
```

### Manual Docker Build & Run
```bash
# Build Docker image
docker build -t ai-voice-bot:1.0.0 .

# Run container with environment configuration
docker run -d \
  -p 8000:8000 \
  --name ai-voice-bot \
  --env-file .env \
  ai-voice-bot:1.0.0
```

---

## 3. Production Telephony Integration

The platform accepts standard 16kHz PCM16 bidirectional audio streams over WebSockets (`/ws/voice`).

### 3.1 Asterisk PBX with AudioSocket
Asterisk connects via dialplan using the AudioSocket application:
```asterisk
; extensions.conf
exten => 1000,1,Answer()
 same => n,AudioSocket(d38b4c09-897b-4020-8025-ea3b71946358,10.0.1.50:8000)
 same => n,Hangup()
```

### 3.2 Twilio Media Streams
Configure Twilio TwiML Voice Webhook to fork audio:
```xml
<Response>
    <Connect>
        <Stream url="wss://your-voice-bot-domain.com/ws/voice" />
    </Connect>
</Response>
```

### 3.3 FreeSWITCH
Using `mod_audio_fork` to stream channel audio bidirectionally to `/ws/voice`.

---

## 4. Environment Variables Reference

| Variable | Default | Purpose |
|---|---|---|
| `WEBSOCKET_HOST` | `0.0.0.0` | Host IP binding for FastAPI server |
| `WEBSOCKET_PORT` | `8000` | Port for HTTP & WebSocket connections |
| `ENABLE_MOCK_STT` | `True` | Set to `False` to activate DeepSpeech STT |
| `ENABLE_MOCK_LLM` | `True` | Set to `False` to activate Gemini 2.5 Flash |
| `ENABLE_MOCK_TTS` | `True` | Set to `False` to activate Cartesia TTS |
| `GEMINI_API_KEY` | `None` | Google AI Studio or Vertex AI API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model version |
| `CARTESIA_API_KEY` | `None` | Cartesia TTS API key |
| `CARTESIA_VOICE_ID` | `a0e99841...` | Cartesia multilingual conversational voice |
| `VAD_THRESHOLD` | `0.5` | Sensitivity threshold for speech detection (0.0-1.0) |
| `LOG_LEVEL` | `INFO` | Application log level (DEBUG, INFO, WARNING, ERROR) |

---

## 5. Health Checks & Prometheus Scrapers

The platform exposes three monitoring endpoints:
- `GET /health` — Liveness probe (HTTP 200 `{"status": "healthy"}`)
- `GET /ready` — Readiness probe verifying provider status and configuration
- `GET /metrics` — Exposes active sessions, total completed calls, barge-in counts, and p50/p95/p99 latency percentiles
