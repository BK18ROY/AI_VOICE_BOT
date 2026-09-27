# Conversational Voice AI Platform — Troubleshooting & Operations Guide

This guide provides diagnostics, root causes, and remediation steps for common operational issues encountered in real-time voice AI pipelines.

---

## 1. Audio Stuttering & Jitter Underruns

### Symptoms
- Caller hears choppy, robotic, or repeating audio slices during assistant playback.

### Root Causes & Fixes
1. **Network Frame Sizing Mismatch**:
   - Ensure audio is transmitted in **20ms slices (640 bytes for 16kHz PCM16)**. Larger chunk sizes (e.g. 500ms) induce bursty playback queues.
2. **Event Loop Starvation**:
   - Blocking synchronous operations inside `async def` pipeline handlers starve audio dispatch.
   - *Fix*: Ensure all disk I/O, network requests, and tool queries are executed asynchronously or delegated to `asyncio.to_thread`.
3. **Buffer Underruns**:
   - TTS synthesis generation is slower than real-time playback (Real-Time Factor RTF > 1.0).
   - *Fix*: Pre-buffer the initial 200ms of synthesized audio before initiating playback over WebSocket.

---

## 2. Latency Spikes (High End-to-End Latency)

### Diagnostics
Run the automated latency benchmark to locate the bottleneck:
```bash
python main.py benchmark --runs 10
```
Inspect the metric breakdown:
- `stt_latency_ms`: Should be <100ms in streaming mode.
- `llm_ttft_ms`: Should be <100ms with Gemini 2.5 Flash.
- `tts_ttfa_ms`: Should be <150ms with Cartesia Sonic.

### Solutions
- **High VAD Latency**: If the bot takes too long to respond after the caller stops speaking, lower `VAD_MIN_SILENCE_DURATION` from `0.5` to `0.35` in `.env`.
- **High LLM TTFT**: Check network connectivity to Gemini endpoints (`us-central1` or nearest region). Ensure prompt system instructions are concise (<500 tokens).

---

## 3. Barge-In False Positives & Echo Feedback

### Symptoms
- The bot stops talking immediately as soon as it begins speaking, even when the user didn't speak.

### Root Causes & Fixes
1. **Acoustic Echo Leakage**:
   - Caller speaker audio is picked up by the caller microphone and looped back to the server.
   - *Fix*: Enable Acoustic Echo Cancellation (AEC) on the client side (e.g., WebRTC `echoCancellation: true` or telephony hardware AEC).
2. **VAD Threshold Too Sensitive**:
   - Background office noise or breathing trips `vad_threshold`.
   - *Fix*: Increase `VAD_THRESHOLD` in `.env` from `0.5` to `0.6` or `0.65`. Increase `VAD_MIN_SPEECH_DURATION` from `0.25` to `0.35`.

---

## 4. Provider Rate Limits & Circuit Breaker Tripping

### Symptoms
- Logs indicate `circuit_breaker_opened` and assistant uses fallback canned responses.

### Solutions
- Inspect structured logs for HTTP 429 (Too Many Requests) or 503 (Service Unavailable):
  ```bash
  cat logs/voice_bot.log | grep -i "circuit_breaker"
  ```
- The built-in `CircuitBreaker` automatically prevents hammering failing upstream providers and tests recovery after 20 seconds.
- Verify API quota on Google Cloud Console (Gemini) or Cartesia dashboard.

---

## 5. Correlating Logs with Session IDs

Every conversational session has a unique UUID attached to all log lines, metrics, and audio chunks:
```json
{
  "timestamp": "2026-09-27T19:24:16.879Z",
  "level": "info",
  "event": "turn_completed",
  "session_id": "demo_sess_2312",
  "e2e_latency_ms": 96.5,
  "llm_ttft_ms": 16.2,
  "tts_ttfa_ms": 96.3
}
```
Filter logs by session ID:
```bash
python scripts/test_pipeline.py | grep "session_id=demo_sess_2312"
```
