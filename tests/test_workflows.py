"""Unit tests for support workflows, intent routing, and LangGraph orchestration."""

import pytest
from app.conversation.graph import ConversationWorkflowGraph
from app.conversation.intent_router import IntentRouter
from app.conversation.state import create_initial_state
from app.schemas.conversation import IntentType, LanguageCode
from app.workflows.dealer_support import DealerSupportWorkflow
from app.workflows.finance_support import FinanceSupportWorkflow
from app.workflows.product_support import ProductSupportWorkflow
from app.workflows.roadside_assistance import RoadsideAssistanceWorkflow


def test_intent_routing_classification():
    """Verify that intent router categorizes queries into the 4 primary workflows."""
    router = IntentRouter()

    intent_prod, _ = router.route("Can you check the warranty status for SN-5521?")
    assert intent_prod == IntentType.PRODUCT_SUPPORT

    intent_fin, _ = router.route("Please tell me my EMI status for account ACC-101.")
    assert intent_fin == IntentType.FINANCE_SUPPORT

    intent_rsa, _ = router.route("My car has broken down on Highway 48, I need roadside assistance.")
    assert intent_rsa == IntentType.ROADSIDE_ASSISTANCE

    intent_dealer, _ = router.route("Where is the nearest authorized dealer and workshop?")
    assert intent_dealer == IntentType.DEALER_SUPPORT


@pytest.mark.asyncio
async def test_product_support_workflow():
    """Verify product support workflow runs tools and outputs warranty details."""
    wf = ProductSupportWorkflow()
    state = create_initial_state("sess_prod")

    res = await wf.process("Check warranty for SN-5521", state=state, language=LanguageCode.EN)
    assert res.workflow_name == "product_support"
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].tool_name == "get_product_warranty"
    assert "SN-5521" in res.response_text
    assert "2027" in res.response_text


@pytest.mark.asyncio
async def test_finance_support_workflow():
    """Verify finance support workflow handles EMI inquiry."""
    wf = FinanceSupportWorkflow()
    state = create_initial_state("sess_fin")

    res = await wf.process("What is my EMI for ACC-101?", state=state, language=LanguageCode.EN)
    assert res.workflow_name == "finance_support"
    assert len(res.tool_calls) >= 1
    assert "24,500" in res.response_text or "installment" in res.response_text.lower()


@pytest.mark.asyncio
async def test_roadside_assistance_workflow():
    """Verify roadside assistance workflow dispatches emergency rescue."""
    wf = RoadsideAssistanceWorkflow()
    state = create_initial_state("sess_rsa")

    res = await wf.process("Emergency! Flat tire on Highway 48", state=state, language=LanguageCode.EN)
    assert res.workflow_name == "roadside_assistance"
    assert len(res.tool_calls) >= 1
    assert "dispatched" in res.response_text.lower() or "rescue" in res.response_text.lower() or "assistance" in res.response_text.lower()


@pytest.mark.asyncio
async def test_dealer_support_workflow():
    """Verify dealer support workflow checks job card status."""
    wf = DealerSupportWorkflow()
    state = create_initial_state("sess_dealer")

    res = await wf.process("Check status of job card JC-7711", state=state, language=LanguageCode.EN)
    assert res.workflow_name == "dealer_support"
    assert len(res.tool_calls) >= 1
    assert "JC-7711" in res.response_text or "inspection" in res.response_text.lower() or "workshop" in res.response_text.lower()


@pytest.mark.asyncio
async def test_langgraph_full_orchestration():
    """Verify LangGraph compiles and runs a turn through the entire graph."""
    graph = ConversationWorkflowGraph()
    state = create_initial_state("sess_graph")

    # Run LangGraph turn
    input_data = {
        "session_id": "sess_graph",
        "user_text": "Check warranty for SN-5521",
        "language": "en",
        "intent": "product_support",
        "active_workflow": None,
        "is_follow_up": False,
        "context_retrieved": False,
        "tool_calls": [],
        "tool_results": [],
        "response_text": "",
        "is_completed": False,
        "error": None,
    }

    final_state = await graph.graph.ainvoke(input_data)
    assert final_state["response_text"] != ""
    assert "SN-5521" in final_state["response_text"] or "warranty" in final_state["response_text"].lower()
