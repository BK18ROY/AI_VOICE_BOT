"""Telephony and WebSocket audio transport abstraction."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from fastapi import WebSocket
from app.observability.logger import logger
from app.schemas.responses import ServerEventType, WebSocketServerEvent


class BaseAudioTransport(ABC):
    """Abstract interface for audio ingestion and delivery."""

    @abstractmethod
    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send synthesized audio back to caller."""
        pass

    @abstractmethod
    async def send_event(self, event_type: ServerEventType, data: Optional[Dict[str, Any]] = None) -> None:
        """Send signaling or status event."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection."""
        pass

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Check if transport channel is alive."""
        pass


class WebSocketAudioTransport(BaseAudioTransport):
    """WebSocket implementation for web callers and Asterisk AudioSocket bridge."""

    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self._is_active = True
        self._write_lock = asyncio.Lock()

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send raw binary audio frame to client."""
        if not self._is_active or not audio_bytes:
            return
        async with self._write_lock:
            try:
                await self.websocket.send_bytes(audio_bytes)
            except Exception as e:
                logger.warning("transport_send_audio_failed", session_id=self.session_id, error=str(e))
                self._is_active = False

    async def send_event(self, event_type: ServerEventType, data: Optional[Dict[str, Any]] = None) -> None:
        """Send JSON metadata event to client."""
        if not self._is_active:
            return
        import time
        event = WebSocketServerEvent(
            event=event_type,
            session_id=self.session_id,
            timestamp=time.time(),
            data=data or {},
        )
        async with self._write_lock:
            try:
                await self.websocket.send_text(event.model_dump_json())
            except Exception as e:
                logger.warning("transport_send_event_failed", session_id=self.session_id, event=event_type.value, error=str(e))
                self._is_active = False

    async def close(self) -> None:
        """Safely disconnect websocket."""
        self._is_active = False
        try:
            await self.websocket.close()
        except Exception:
            pass

    @property
    def is_active(self) -> bool:
        return self._is_active
