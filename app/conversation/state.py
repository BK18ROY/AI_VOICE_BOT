"""State models and session factories for conversational sessions."""

import uuid
from typing import Optional
from app.schemas.conversation import (
    ConversationState,
    ConversationTurn,
    IntentType,
    LanguageCode,
    MessageRole,
    ToolCall,
    ToolResult,
)


def create_initial_state(
    session_id: Optional[str] = None,
    caller_id: str = "caller_default",
    initial_language: LanguageCode = LanguageCode.EN,
    workflow_hint: Optional[str] = None,
) -> ConversationState:
    """Instantiate a clean initial ConversationState for a new call."""
    sid = session_id or str(uuid.uuid4())
    return ConversationState(
        session_id=sid,
        caller_id=caller_id,
        detected_language=initial_language,
        conversation_history=[],
        current_intent=IntentType.GREETING,
        active_workflow=workflow_hint,
        current_turn=0,
        interruption_state=False,
        last_user_transcript=None,
        last_assistant_response=None,
        latency_metrics={},
        tool_results=[],
        error_state=None,
        is_active=True,
    )
