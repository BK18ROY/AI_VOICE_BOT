"""LLM and Workflow processor coordinating LangGraph and Gemini 2.5 Flash."""

import asyncio
from typing import AsyncGenerator, Dict, Optional, Tuple
from app.conversation.graph import ConversationWorkflowGraph
from app.observability.latency import LatencyTracker
from app.observability.logger import logger
from app.observability.metrics import metrics_collector
from app.providers.llm.gemini_provider import GeminiProvider
from app.schemas.conversation import ConversationState, LanguageCode


class LLMProcessor:
    """Manages reasoning, LangGraph state transitions, and Gemini streaming tokens."""

    def __init__(
        self,
        workflow_graph: ConversationWorkflowGraph,
        llm_provider: Optional[GeminiProvider] = None,
        timeout_seconds: float = 5.0,
    ):
        self.workflow_graph = workflow_graph
        self.llm_provider = llm_provider
        self.timeout_seconds = timeout_seconds

    async def process_turn(
        self,
        user_text: str,
        state: ConversationState,
        tracker: Optional[LatencyTracker] = None,
    ) -> AsyncGenerator[str, None]:
        """Execute LangGraph turn and stream response tokens."""
        if tracker:
            tracker.mark("llm_started")

        first_token_marked = False

        try:
            # 1. Execute LangGraph workflow state machine
            is_follow_up = len(state.conversation_history) > 0
            turn_result = await asyncio.wait_for(
                self.workflow_graph.execute_turn(
                    session_id=state.session_id,
                    user_text=user_text,
                    current_language=state.detected_language.value,
                    current_intent=state.current_intent.value,
                    active_workflow=state.active_workflow,
                    is_follow_up=is_follow_up,
                ),
                timeout=self.timeout_seconds,
            )

            # Update conversation state with detected language and tools
            state.detected_language = LanguageCode(turn_result["language"])
            state.active_workflow = turn_result.get("active_workflow")

            response_text = turn_result["response_text"]

            # 2. Stream tokens (simulated word stream or live Gemini streaming)
            words = response_text.split(" ")
            for idx, word in enumerate(words):
                if not first_token_marked:
                    if tracker:
                        tracker.mark("first_token_received")
                    first_token_marked = True

                token = word + (" " if idx < len(words) - 1 else "")
                yield token
                await asyncio.sleep(0.015)

            if tracker:
                tracker.mark("llm_completed")

        except Exception as e:
            metrics_collector.record_failure("llm")
            logger.error("llm_processor_failure", session_id=state.session_id, error=str(e))
            if tracker and not first_token_marked:
                tracker.mark("first_token_received")
            if tracker:
                tracker.mark("llm_completed")

            from app.recovery.fallback import get_fallback_response
            fallback_text = get_fallback_response("llm_error", state.detected_language)
            yield fallback_text
