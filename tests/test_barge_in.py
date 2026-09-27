"""Unit tests for Barge-in and interruption handling."""

import asyncio
import pytest
from app.pipeline.interruption_handler import InterruptionHandler


@pytest.mark.asyncio
async def test_no_barge_in_when_bot_idle():
    """Verify that speech while bot is idle is not flagged as an interruption."""
    handler = InterruptionHandler()
    assert handler.bot_is_speaking is False

    interrupted = await handler.handle_user_speech_start("test_session")
    assert interrupted is False
    assert handler.interruption_count == 0


@pytest.mark.asyncio
async def test_barge_in_cancels_active_task():
    """Verify barge-in halts ongoing speech synthesis and fires callback."""
    callback_fired = []

    async def on_interrupt():
        callback_fired.append(True)

    handler = InterruptionHandler(on_interrupt_callback=on_interrupt)

    # Simulate ongoing TTS task
    async def ongoing_speech():
        await asyncio.sleep(10.0)

    task = asyncio.create_task(ongoing_speech())
    handler.set_bot_speaking(True, active_task=task)

    assert handler.bot_is_speaking is True
    assert not task.done()

    # User begins speaking
    interrupted = await handler.handle_user_speech_start("session_123")
    await asyncio.sleep(0.01)

    assert interrupted is True
    assert handler.interruption_count == 1
    assert handler.bot_is_speaking is False
    assert task.cancelled() or task.done()
    assert len(callback_fired) == 1


@pytest.mark.asyncio
async def test_interruption_handler_reset():
    """Verify state reset clears flags and tasks."""
    handler = InterruptionHandler()
    dummy_task = asyncio.create_task(asyncio.sleep(1.0))
    handler.set_bot_speaking(True, active_task=dummy_task)

    assert handler.bot_is_speaking is True
    handler.reset()
    assert handler.bot_is_speaking is False
    dummy_task.cancel()
