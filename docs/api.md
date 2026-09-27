# Conversational Voice AI Platform — API & WebSocket Protocol Reference

This document provides complete technical specifications for the REST endpoints and the real-time bidirectional WebSocket streaming protocol.

---

## 1. REST API Endpoints

### 1.1 Root Metadata
- **URL**: `GET /`
- **Description**: Returns service overview, version, active operating mode, and active providers.
- **Response**:
```json
{
  "service": "ai-voice-bot",
  "version": "1.0.0",
  "description": "Real-Time Conversational AI Voice Platform",
  "endpoints": {
    "health": "/health",
    "readiness": "/ready",
    "metrics": "/metrics",
    "websocket_voice": "/ws/voice",
    "docs": "/docs"
  },
  "mode": "mock",
  "providers": {
    "stt": "mock",
    "llm": "mock",
    "tts": "mock"
  }
}
```

### 1.2 Liveness Probe
- **URL**: `GET /health`
- **Description**: Kubernetes / Docker liveness probe returning HTTP 200 when service is running.
- **Response**:
```json
{
  "status": "healthy",
  "service": "ai-voice-bot",
  "timestamp": 1727464800.0,
  "version": "1.0.0"
}
```

### 1.3 Readiness Probe
- **URL**: `GET /ready`
- **Description**: Verifies provider configuration, VAD parameters, and storage paths.
- **Response**:
```json
{
  "status": "ready",
  "providers": {
    "stt": "mock",
    "llm": "mock",
    "tts": "mock",
    "vad": "silero_compatible"
  },
  "environment": "mock",
  "details": {
    "websocket_port": 8000,
    "vad_threshold": 0.5,
    "recordings_dir": "outputs/audio"
  }
}
```

### 1.4 Real-Time Metrics Probe
- **URL**: `GET /metrics`
- **Description**: Exposes call volumes, active sessions, interruption counts, and latency statistics.
- **Response**:
```json
{
  "active_sessions": 0,
  "total_sessions": 25,
  "successful_sessions": 25,
  "failed_sessions": 0,
  "barge_in_count": 4,
  "stt_failures": 0,
  "llm_failures": 0,
  "tts_failures": 0,
  "latency_percentiles": {
    "p50_ms": 86.4,
    "p90_ms": 105.1,
    "p95_ms": 108.8,
    "p99_ms": 111.7
  }
}
```

---

## 2. WebSocket Voice Streaming Protocol

- **Endpoint**: `ws://<host>:<port>/ws/voice`
- **Protocols Supported**: Binary PCM Audio Frames + UTF-8 JSON Control Messages.

### 2.1 Binary Audio Framing
- **Encoding**: 16-bit Linear PCM (`int16`), Little Endian
- **Sampling Rate**: 16,000 Hz
- **Channels**: 1 (Mono)
- **Frame Duration**: 20 milliseconds (320 samples = 640 bytes per message)

### 2.2 Client-to-Server JSON Messages

#### Session Start
```json
{
  "type": "session_start",
  "payload": {
    "caller_id": "caller_alex_99",
    "initial_language": "en"
  }
}
```

#### Direct Text Input (Bypassing Audio)
```json
{
  "type": "text_input",
  "payload": {
    "text": "Can you check warranty status for serial SN-5521?"
  }
}
```

#### Manual Barge-in Trigger
```json
{
  "type": "barge_in",
  "payload": {}
}
```

#### Session End
```json
{
  "type": "session_end",
  "payload": {}
}
```

### 2.3 Server-to-Client Events

#### Session Initialized
```json
{
  "event": "session_start",
  "data": {
    "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "status": "ready",
    "sample_rate": 16000,
    "mock_mode": true
  }
}
```

#### Final Speech Recognition Transcript
```json
{
  "event": "transcript_final",
  "data": {
    "transcript": "Check warranty for SN-5521",
    "confidence": 0.98
  }
}
```

#### LLM Token Stream
```json
{
  "event": "llm_token",
  "data": {
    "token": "Your "
  }
}
```

#### Turn & TTS Synthesis Complete
```json
{
  "event": "tts_complete",
  "data": {
    "latency_breakdown": {
      "vad_latency_ms": 22.1,
      "stt_latency_ms": 0.0,
      "llm_ttft_ms": 16.2,
      "llm_total_ms": 480.0,
      "tts_ttfa_ms": 96.4,
      "end_to_end_ms": 96.5
    }
  }
}
```

#### Barge-In Cancellation Notice
```json
{
  "event": "barge_in",
  "data": {
    "message": "Assistant audio cancelled due to user speech interruption."
  }
}
```
