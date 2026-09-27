"""Conversation schemas and state models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LanguageCode(str, Enum):
    """Supported conversational languages."""
    EN = "en"
    HI = "hi"
    HINGLISH = "hinglish"


class IntentType(str, Enum):
    """Primary intent categories for customer support."""
    GREETING = "greeting"
    PRODUCT_SUPPORT = "product_support"
    FINANCE_SUPPORT = "finance_support"
    ROADSIDE_ASSISTANCE = "roadside_assistance"
    DEALER_SUPPORT = "dealer_support"
    GENERAL_QUERY = "general_query"
    FALLBACK = "fallback"


class MessageRole(str, Enum):
    """Role of speaker in turn."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolCall(BaseModel):
    """Structured tool execution request."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    tool_call_id: Optional[str] = None


class ToolResult(BaseModel):
    """Structured tool execution result."""
    tool_name: str
    result: Any
    is_error: bool = False
    error_message: Optional[str] = None


class ConversationTurn(BaseModel):
    """Single turn in a conversation."""
    turn_id: int
    role: MessageRole
    content: str
    language: LanguageCode = LanguageCode.EN
    timestamp: float
    latency_ms: Optional[float] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)


class ConversationState(BaseModel):
    """Complete conversational state tracked across pipeline."""

    session_id: str
    caller_id: str = "caller_anonymous"
    detected_language: LanguageCode = LanguageCode.EN
    conversation_history: List[ConversationTurn] = Field(default_factory=list)
    current_intent: IntentType = IntentType.GREETING
    active_workflow: Optional[str] = None
    current_turn: int = 0
    interruption_state: bool = False
    last_user_transcript: Optional[str] = None
    last_assistant_response: Optional[str] = None
    latency_metrics: Dict[str, Any] = Field(default_factory=dict)
    tool_results: List[ToolResult] = Field(default_factory=list)
    error_state: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_turn(
        self,
        role: MessageRole,
        content: str,
        language: Optional[LanguageCode] = None,
        latency_ms: Optional[float] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        tool_results: Optional[List[ToolResult]] = None,
    ) -> ConversationTurn:
        """Append a new turn to conversation history."""
        self.current_turn += 1
        import time
        turn = ConversationTurn(
            turn_id=self.current_turn,
            role=role,
            content=content,
            language=language or self.detected_language,
            timestamp=time.time(),
            latency_ms=latency_ms,
            tool_calls=tool_calls or [],
            tool_results=tool_results or [],
        )
        self.conversation_history.append(turn)
        if role == MessageRole.USER:
            self.last_user_transcript = content
        elif role == MessageRole.ASSISTANT:
            self.last_assistant_response = content
        return turn
