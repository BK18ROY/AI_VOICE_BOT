"""LangGraph-based conversation and workflow state machine."""

import asyncio
from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END

from app.conversation.intent_router import IntentRouter
from app.conversation.language_detector import LanguageDetector
from app.schemas.conversation import ConversationState, IntentType, LanguageCode, ToolCall, ToolResult
from app.workflows.dealer_support import DealerSupportWorkflow
from app.workflows.finance_support import FinanceSupportWorkflow
from app.workflows.product_support import ProductSupportWorkflow
from app.workflows.roadside_assistance import RoadsideAssistanceWorkflow


class ConversationGraphState(TypedDict):
    """LangGraph execution state dictionary."""
    session_id: str
    user_text: str
    language: str
    intent: str
    active_workflow: Optional[str]
    is_follow_up: bool
    context_retrieved: bool
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    response_text: str
    is_completed: bool
    error: Optional[str]


class ConversationWorkflowGraph:
    """Orchestrates turn processing using an executable LangGraph StateGraph."""

    def __init__(self):
        self.language_detector = LanguageDetector()
        self.intent_router = IntentRouter()

        # Initialize workflows
        self.workflows = {
            "product_support": ProductSupportWorkflow(),
            "finance_support": FinanceSupportWorkflow(),
            "roadside_assistance": RoadsideAssistanceWorkflow(),
            "dealer_support": DealerSupportWorkflow(),
        }

        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(ConversationGraphState)

        # Add Nodes
        workflow.add_node("receive_user_input", self._node_receive_user_input)
        workflow.add_node("detect_language", self._node_detect_language)
        workflow.add_node("classify_intent", self._node_classify_intent)
        workflow.add_node("context_retrieval", self._node_context_retrieval)
        workflow.add_node("workflow_router", self._node_workflow_router)
        workflow.add_node("execute_business_tools", self._node_execute_business_tools)
        workflow.add_node("generate_response", self._node_generate_response)
        workflow.add_node("prepare_tts", self._node_prepare_tts)

        # Edges
        workflow.add_edge(START, "receive_user_input")
        workflow.add_edge("receive_user_input", "detect_language")
        workflow.add_edge("detect_language", "context_retrieval")

        # Conditional branch: if follow-up and active workflow exists, skip re-classifying intent
        def route_after_context(state: ConversationGraphState) -> str:
            if state.get("is_follow_up") and state.get("active_workflow"):
                return "workflow_router"
            return "classify_intent"

        workflow.add_conditional_edges(
            "context_retrieval",
            route_after_context,
            {
                "workflow_router": "workflow_router",
                "classify_intent": "classify_intent",
            },
        )

        workflow.add_edge("classify_intent", "workflow_router")
        workflow.add_edge("workflow_router", "execute_business_tools")
        workflow.add_edge("execute_business_tools", "generate_response")
        workflow.add_edge("generate_response", "prepare_tts")
        workflow.add_edge("prepare_tts", END)

        return workflow.compile()

    async def _node_receive_user_input(self, state: ConversationGraphState) -> Dict[str, Any]:
        """Validate and clean incoming user utterance."""
        text = state.get("user_text", "").strip()
        return {"user_text": text, "error": None}

    async def _node_detect_language(self, state: ConversationGraphState) -> Dict[str, Any]:
        """Identify language and detect language switching directives."""
        current_lang = LanguageCode(state.get("language", "en"))
        detected_lang, _ = self.language_detector.detect(state["user_text"], current_language=current_lang)
        return {"language": detected_lang.value}

    async def _node_context_retrieval(self, state: ConversationGraphState) -> Dict[str, Any]:
        """Retrieve contextual information for multi-turn dialogs."""
        # Active workflow preserved if already set
        return {"context_retrieved": True}

    async def _node_classify_intent(self, state: ConversationGraphState) -> Dict[str, Any]:
        """Classify user intent if not already pinned to an active workflow."""
        current_intent = IntentType(state.get("intent", "greeting"))
        intent, _ = self.intent_router.route(state["user_text"], current_intent=current_intent)

        # Map intent to workflow key
        workflow_map = {
            IntentType.PRODUCT_SUPPORT: "product_support",
            IntentType.FINANCE_SUPPORT: "finance_support",
            IntentType.ROADSIDE_ASSISTANCE: "roadside_assistance",
            IntentType.DEALER_SUPPORT: "dealer_support",
        }
        wf_name = workflow_map.get(intent)
        return {"intent": intent.value, "active_workflow": wf_name}

    async def _node_workflow_router(self, state: ConversationGraphState) -> Dict[str, Any]:
        """Route to specific workflow handler or general dialog."""
        wf_name = state.get("active_workflow")
        if not wf_name or wf_name not in self.workflows:
            # Default to roadside if emergency, else product support
            wf_name = "product_support"
        return {"active_workflow": wf_name}

    async def _node_execute_business_tools(self, state: ConversationGraphState) -> Dict[str, Any]:
        """Execute domain workflow tools."""
        wf_name = state.get("active_workflow", "product_support")
        wf = self.workflows.get(wf_name, self.workflows["product_support"])

        # Construct minimal ConversationState for tool execution
        c_state = ConversationState(
            session_id=state["session_id"],
            detected_language=LanguageCode(state["language"]),
            current_intent=IntentType(state.get("intent", "greeting")),
            active_workflow=wf_name,
        )

        wf_result = await wf.process(
            user_text=state["user_text"],
            state=c_state,
            language=LanguageCode(state["language"]),
        )

        tool_calls = [tc.model_dump() for tc in wf_result.tool_calls]
        tool_results = [tr.model_dump() for tr in wf_result.tool_results]

        return {
            "response_text": wf_result.response_text,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "is_completed": wf_result.is_completed,
        }

    async def _node_generate_response(self, state: ConversationGraphState) -> Dict[str, Any]:
        """Verify response formatting for speech clarity."""
        text = state.get("response_text", "")
        # Remove markdown stars or hashtags that TTS cannot speak cleanly
        cleaned = text.replace("*", "").replace("#", "").strip()
        return {"response_text": cleaned}

    async def _node_prepare_tts(self, state: ConversationGraphState) -> Dict[str, Any]:
        """Prepare finalized text for streaming to TTS synthesizer."""
        return {"is_completed": True}

    async def execute_turn(
        self,
        session_id: str,
        user_text: str,
        current_language: str = "en",
        current_intent: str = "greeting",
        active_workflow: Optional[str] = None,
        is_follow_up: bool = False,
    ) -> Dict[str, Any]:
        """Run the compiled LangGraph pipeline for a single conversational turn."""
        initial_input: ConversationGraphState = {
            "session_id": session_id,
            "user_text": user_text,
            "language": current_language,
            "intent": current_intent,
            "active_workflow": active_workflow,
            "is_follow_up": is_follow_up,
            "context_retrieved": False,
            "tool_calls": [],
            "tool_results": [],
            "response_text": "",
            "is_completed": False,
            "error": None,
        }

        # Invoke LangGraph async runner
        final_state = await self.graph.ainvoke(initial_input)
        return final_state
