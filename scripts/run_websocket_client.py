"""Simulated WebSocket caller client for testing real-time audio and text streaming."""

import asyncio
import json
import os
import sys
import websockets
import soundfile as sf
from app.audio.audio_utils import float32_to_pcm16


async def stream_audio_file(ws, audio_path: str, chunk_ms: int = 20):
    """Slice a WAV file into 20ms PCM frames and stream in real time."""
    data, sr = sf.read(audio_path, dtype='float32')
    if data.ndim > 1:
        data = data.mean(axis=1)

    pcm_bytes = float32_to_pcm16(data)
    bytes_per_chunk = int(sr * (chunk_ms / 1000.0) * 2)

    print(f"[*] Streaming audio file: {audio_path} ({len(pcm_bytes)} bytes)...")
    offset = 0
    while offset < len(pcm_bytes):
        chunk = pcm_bytes[offset: offset + bytes_per_chunk]
        await ws.send(chunk)
        offset += bytes_per_chunk
        await asyncio.sleep(chunk_ms / 1000.0)
    print("[*] Finished streaming audio file.")


async def listen_server_events(ws):
    """Listen for incoming server events and synthesized audio frames."""
    total_audio_bytes = 0
    try:
        async for msg in ws:
            if isinstance(msg, bytes):
                total_audio_bytes += len(msg)
                print(f"[AUDIO] Received {len(msg)} synthesized bytes (Total: {total_audio_bytes} bytes)")
            else:
                event = json.loads(msg)
                evt_type = event.get("event")
                data = event.get("data", {})
                if evt_type == "transcript_final":
                    print(f"\n[TRANSCRIPT] Caller said: '{data.get('transcript')}'")
                elif evt_type == "llm_token":
                    print(data.get("token", ""), end="", flush=True)
                elif evt_type == "tts_complete":
                    print(f"\n[TTS COMPLETE] Latencies: {data.get('latency_breakdown')}")
                elif evt_type == "barge_in":
                    print("\n[BARGE-IN] Bot playback interrupted by caller speech!")
                elif evt_type == "session_start":
                    print(f"[*] Connected. Session ID: {data.get('session_id')}")
    except websockets.exceptions.ConnectionClosed:
        print("\n[*] Connection closed by server.")


async def main():
    uri = "ws://127.0.0.1:8000/ws/voice"
    print(f"[*] Connecting to AI Voice Bot at {uri}...")

    try:
        async with websockets.connect(uri) as ws:
            listener_task = asyncio.create_task(listen_server_events(ws))

            # Send session start
            await ws.send(json.dumps({
                "type": "session_start",
                "payload": {"caller_id": "client_tester", "initial_language": "en"}
            }))
            await asyncio.sleep(0.5)

            # Check if demo audio exists
            audio_path = "data/audio/demo_speech.wav"
            if os.path.exists(audio_path):
                await stream_audio_file(ws, audio_path)
            else:
                # Text input fallback
                await ws.send(json.dumps({
                    "type": "text_input",
                    "payload": {"text": "Can you check the warranty status for SN-5521?"}
                }))

            # Allow time for response
            await asyncio.sleep(3.0)

            # Test text query in Hindi/Hinglish
            print("\n[*] Sending Hinglish follow-up query...")
            await ws.send(json.dumps({
                "type": "text_input",
                "payload": {"text": "Achha Hindi mein batao meri EMI ka status kya hai?"}
            }))
            await asyncio.sleep(3.0)

            # End session
            await ws.send(json.dumps({"type": "session_end", "payload": {}}))
            await asyncio.sleep(1.0)
            listener_task.cancel()

    except Exception as e:
        print(f"[!] Connection failed: {e}")
        print("[!] Ensure the server is running with 'python main.py server'")


if __name__ == "__main__":
    asyncio.run(main())
