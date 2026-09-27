"""Pipecat-oriented real-time streaming Voice Pipeline."""

import asyncio
import time
from typing import AsyncGenerator, Optional
from app.audio.audio_buffer import AudioRingBuffer
from app.observability.latency import LatencyTracker
from app.observability.logger import get_session_logger, logger
from app.observability.metrics import metrics_collector
from app.pipeline.audio_transport import BaseAudioTransport
from app.pipeline.interruption_handler import InterruptionHandler
from app.pipeline.llm_processor import LLMProcessor
from app.pipeline.stt_processor import STTProcessor
from app.pipeline.tts_processor import TTSProcessor
from app.pipeline.vad_processor import VADProcessor
from app.schemas.audio import VADEventType
from app.schemas.conversation import ConversationState, MessageRole
from app.schemas.responses import ServerEventType


class VoicePipeline:
    """Real-time voice processing pipeline connecting VAD, STT, LangGraph/LLM, and TTS with barge-in support."""

    def __init__(
        self,
        session_id: str,
        transport: BaseAudioTransport,
        vad: VADProcessor,
        stt: STTProcessor,
        llm: LLMProcessor,
        tts: TTSProcessor,
        state: ConversationState,
        interruption_handler: InterruptionHandler,
        audio_buffer: Optional[AudioRingBuffer] = None,
    ):
        self.session_id = session_id
        self.transport = transport
        self.vad = vad
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.state = state
        self.interruption_handler = interruption_handler
        self.audio_buffer = audio_buffer or AudioRingBuffer()
        self.log = get_session_logger(session_id)

        # Connect interruption callback to flush audio and signal client
        self.interruption_handler.on_interrupt_callback = self._on_barge_in_interrupted

        self._active_turn_task: Optional[asyncio.Task] = None
        self._turn_counter = 0

    async def _on_barge_in_interrupted(self) -> None:
        """Callback executed when barge-in is triggered."""
        self.log.info("barge_in_flush_and_cancel")
        self.tts.cancel()
        await self.audio_buffer.clear()
        await self.transport.send_event(ServerEventType.BARGE_IN, {"interrupted": True})

    async def process_audio_frame(self, pcm_bytes: bytes) -> None:
        """Feed incoming audio frame (20-30ms PCM16) into VAD and ring buffer."""
        from app.schemas.audio import AudioChunk, AudioFormat
        chunk = AudioChunk(
            session_id=self.session_id,
            sequence_number=self.audio_buffer._pre_roll.__len__(),
            timestamp=time.time(),
            format=AudioFormat.PCM16,
            raw_bytes=pcm_bytes,
        )
        await self.audio_buffer.add_chunk(chunk)

        vad_res = self.vad.process_frame(pcm_bytes)

        if vad_res.event_type == VADEventType.SPEECH_START:
            self.log.info("vad_speech_start_detected", prob=vad_res.probability)
            # Check for barge-in against bot speech output
            was_interrupted = await self.interruption_handler.handle_user_speech_start(self.session_id)
            if was_interrupted:
                self.log.info("barge_in_cancelled_active_bot_response")

            await self.audio_buffer.start_utterance()
            await self.transport.send_event(ServerEventType.SPEECH_START, {"timestamp": vad_res.timestamp})

        elif vad_res.event_type == VADEventType.SPEECH_END:
            self.log.info("vad_speech_end_detected", prob=vad_res.probability)
            await self.transport.send_event(ServerEventType.SPEECH_END, {"timestamp": vad_res.timestamp})
            utterance_pcm = await self.audio_buffer.end_utterance()

            if len(utterance_pcm) > 3200:  # At least 100ms of audio
                self._turn_counter += 1
                task = asyncio.create_task(self.handle_speech_turn(utterance_pcm, self._turn_counter))
                self._active_turn_task = task

    async def handle_speech_turn(self, pcm_bytes: bytes, turn_id: int) -> None:
        """Process a finalized speech segment through STT -> LangGraph/LLM -> TTS -> Audio Transport."""
        tracker = LatencyTracker(self.session_id, turn_id)
        audio_recv_time = tracker.mark("audio_received")
        tracker.mark("vad_detected", audio_recv_time + 0.05)

        self.log.info("speech_turn_started", turn_id=turn_id, bytes=len(pcm_bytes))

        # 1. Speech-to-Text
        stt_result = await self.stt.transcribe_utterance(pcm_bytes, tracker=tracker)
        user_text = stt_result.text.strip()
        self.log.info("stt_transcript_ready", text=user_text, confidence=stt_result.confidence)

        if not user_text:
            self.log.warning("empty_transcript_ignored")
            return

        await self.transport.send_event(
            ServerEventType.TRANSCRIPT_FINAL,
            {"transcript": user_text, "confidence": stt_result.confidence},
        )

        # 2. Add User turn to conversation state
        self.state.add_turn(role=MessageRole.USER, content=user_text)

        # 3. Process LLM & TTS
        await self._synthesize_and_stream_response(user_text, tracker)

    async def process_text_input(self, text: str) -> None:
        """Direct text turn execution (used for fast testing or text-mode clients)."""
        self._turn_counter += 1
        tracker = LatencyTracker(self.session_id, self._turn_counter)
        tracker.mark("audio_received")
        tracker.mark("vad_detected")
        tracker.mark("stt_started")
        tracker.mark("stt_completed")

        self.state.add_turn(role=MessageRole.USER, content=text)
        await self.transport.send_event(
            ServerEventType.TRANSCRIPT_FINAL,
            {"transcript": text, "confidence": 1.0},
        )
        await self._synthesize_and_stream_response(text, tracker)

    async def _synthesize_and_stream_response(self, user_text: str, tracker: LatencyTracker) -> None:
        """Generate response tokens and stream audio slices with active cancellation."""
        current_task = asyncio.current_task()
        self.interruption_handler.set_bot_speaking(True, active_task=current_task)

        await self.transport.send_event(ServerEventType.LLM_START)
        full_assistant_reply = []

        try:
            # 1. Create token stream from LLM processor
            token_gen = self.llm.process_turn(user_text, self.state, tracker=tracker)

            # 2. Tee token generator to collect full reply for state while streaming
            async def streaming_tee() -> AsyncGenerator[str, None]:
                async for token in token_gen:
                    full_assistant_reply.append(token)
                    await self.transport.send_event(ServerEventType.LLM_TOKEN, {"token": token})
                    yield token

            await self.transport.send_event(ServerEventType.TTS_START)

            # 3. Stream synthesized audio chunks to transport
            async for audio_chunk in self.tts.stream_audio_from_tokens(streaming_tee(), tracker=tracker):
                if not self.interruption_handler.bot_is_speaking:
                    self.log.info("tts_audio_delivery_aborted_due_to_interruption")
                    break
                await self.transport.send_audio(audio_chunk)

            # 4. Finalize turn
            reply_text = "".join(full_assistant_reply).strip()
            self.state.add_turn(role=MessageRole.ASSISTANT, content=reply_text)

            breakdown = tracker.calculate()
            metrics_collector.record_turn_latency(breakdown.end_to_end_ms)

            self.log.info(
                "turn_completed",
                e2e_latency_ms=breakdown.end_to_end_ms,
                stt_latency_ms=breakdown.stt_latency_ms,
                llm_ttft_ms=breakdown.llm_ttft_ms,
                tts_ttfa_ms=breakdown.tts_ttfa_ms,
            )

            await self.transport.send_event(
                ServerEventType.TTS_COMPLETE,
                {"latency_breakdown": breakdown.model_dump(), "response_text": reply_text},
            )

        except asyncio.CancelledError:
            self.log.info("turn_cancelled_by_barge_in")
            self.tts.cancel()
        finally:
            self.interruption_handler.set_bot_speaking(False)
