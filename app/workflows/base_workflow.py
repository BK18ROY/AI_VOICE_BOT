"""Base abstraction for customer support workflows."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.conversation import ConversationState, IntentType, LanguageCode, ToolCall, ToolResult


class WorkflowResult(BaseModel):
    """Output produced by workflow execution."""
    workflow_name: str
    intent: IntentType
    response_text: str
    language: LanguageCode
    tool_calls: List[ToolCall] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    is_completed: bool = True
    next_step: Optional[str] = None
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)


class BaseWorkflow(ABC):
    """Abstract base class for all conversational workflows."""

    def __init__(self, name: str, intent: IntentType, description: str):
        self.name = name
        self.intent = intent
        self.description = description

    @abstractmethod
    async def process(
        self,
        user_text: str,
        state: ConversationState,
        language: LanguageCode,
    ) -> WorkflowResult:
        """Process user input within workflow context and execute appropriate tools."""
        pass
