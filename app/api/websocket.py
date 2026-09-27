"""FastAPI WebSocket endpoint for real-time bidirectional voice streaming."""

import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config.settings import get_settings
from app.audio.audio_utils import validate_pcm_chunk
from app.conversation.context_manager import ContextManager
from app.conversation.state import create_initial_state
from app.observability.logger import get_session_logger, logger
from app.observability.metrics import metrics_collector
from app.pipeline.audio_transport import WebSocketAudioTransport
from app.pipeline.pipeline_factory import create_voice_pipeline
from app.schemas.conversation import LanguageCode
from app.schemas.requests import ClientMessageType, WebSocketClientMessage
from app.schemas.responses import ServerEventType

router = APIRouter(tags=["Voice Streaming"])

# Global context manager instance
context_manager = ContextManager(transcripts_dir=get_settings().transcripts_dir)


@router.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """Bidirectional WebSocket streaming endpoint for telephony and web callers."""
    await websocket.accept()

    cfg = get_settings()
    session_id = str(uuid.uuid4())
    log = get_session_logger(session_id)
    log.info("websocket_connected", client=str(websocket.client))

    # Initialize state & transport
    state = create_initial_state(session_id=session_id)
    context_manager.register_session(state)
    metrics_collector.session_started()

    transport = WebSocketAudioTransport(websocket=websocket, session_id=session_id)
    pipeline = create_voice_pipeline(
        session_id=session_id,
        transport=transport,
        state=state,
        settings=cfg,
    )

    # Signal session started
    await transport.send_event(
        ServerEventType.SESSION_START,
        {
            "session_id": session_id,
            "status": "ready",
            "sample_rate": cfg.vad_sample_rate,
            "mock_mode": cfg.enable_mock_stt,
        },
    )

    try:
        while True:
            # Receive either binary audio frame or text control JSON
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                raw_bytes = message["bytes"]
                if not validate_pcm_chunk(raw_bytes, max_bytes=cfg.max_audio_chunk_bytes):
                    await transport.send_event(
                        ServerEventType.ERROR,
                        {"error": "Invalid PCM chunk size or byte alignment"},
                    )
                    continue

                await pipeline.process_audio_frame(raw_bytes)

            elif "text" in message and message["text"]:
                try:
                    payload_dict = json.loads(message["text"])
                    client_msg = WebSocketClientMessage.model_validate(payload_dict)
                except Exception as e:
                    await transport.send_event(ServerEventType.ERROR, {"error": f"Invalid JSON payload: {str(e)}"})
                    continue

                msg_type = client_msg.type

                if msg_type == ClientMessageType.SESSION_START:
                    lang = client_msg.payload.get("initial_language", "en")
                    caller_id = client_msg.payload.get("caller_id", "caller_default")
                    state.detected_language = LanguageCode(lang)
                    state.caller_id = caller_id
                    log.info("session_metadata_updated", caller_id=caller_id, language=lang)

                elif msg_type == ClientMessageType.TEXT_INPUT:
                    text = client_msg.payload.get("text", "").strip()
                    if text:
                        await pipeline.process_text_input(text)

                elif msg_type == ClientMessageType.BARGE_IN:
                    await pipeline.interruption_handler.handle_user_speech_start(session_id)

                elif msg_type == ClientMessageType.PING:
                    await transport.send_event(ServerEventType.PONG)

                elif msg_type == ClientMessageType.SESSION_END:
                    log.info("client_requested_session_end")
                    break

    except WebSocketDisconnect:
        log.info("websocket_disconnected_cleanly")
    except Exception as e:
        log.error("websocket_loop_exception", error=str(e))
        metrics_collector.record_failure("websocket")
    finally:
        # Wrap up post-call analysis
        summary = context_manager.end_session(session_id)
        metrics_collector.session_completed(success=True)
        log.info("session_finalized", total_turns=summary.total_turns if summary else 0)
        await transport.close()
