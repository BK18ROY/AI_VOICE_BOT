"""Dealer and workshop operations support workflow."""

import re
from app.schemas.conversation import ConversationState, IntentType, LanguageCode, ToolCall, ToolResult
from app.tools.dealer_tools import (
    create_dealer_request,
    get_customer_details,
    get_dealer_details,
    get_service_status,
    record_customer_feedback,
)
from app.workflows.base_workflow import BaseWorkflow, WorkflowResult


class DealerSupportWorkflow(BaseWorkflow):
    """Workflow handling dealership inquiries, workshop job card status, and feedback."""

    def __init__(self):
        super().__init__(
            name="dealer_support",
            intent=IntentType.DEALER_SUPPORT,
            description="Coordinates dealership service status, job cards, dealer network, and feedback.",
        )

    async def process(
        self,
        user_text: str,
        state: ConversationState,
        language: LanguageCode,
    ) -> WorkflowResult:
        text_lower = user_text.lower()
        tool_calls = []
        tool_results = []

        if any(w in text_lower for w in ["service", "job card", "status", "ready", "servicing"]):
            jc_match = re.search(r"jc[-\s]?\d+", text_lower)
            jc_id = jc_match.group(0).upper().replace(" ", "") if jc_match else "JC-7711"

            tool_calls.append(ToolCall(tool_name="get_service_status", arguments={"job_card_id": jc_id}))
            res = get_service_status(job_card_id=jc_id)
            tool_results.append(ToolResult(tool_name="get_service_status", result=res))

            if language == LanguageCode.HI:
                msg = f"आपकी गाड़ी का जॉब कार्ड {jc_id} वर्तमान में '{res['service_stage']}' स्टेज पर है। यह {res['estimated_completion_time']} तक तैयार हो जाएगी।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Job card {jc_id} ka status '{res['service_stage']}' hai. Gaadi {res['estimated_completion_time']} tak complete deliver ho jayegi."
            else:
                msg = f"Vehicle job card {jc_id} is in '{res['service_stage']}' stage. Estimated completion is {res['estimated_completion_time']}."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        elif any(w in text_lower for w in ["feedback", "rating", "review", "satisfaction"]):
            rating = 5 if "good" in text_lower or "great" in text_lower or "5" in text_lower else 4
            tool_calls.append(
                ToolCall(
                    tool_name="record_customer_feedback",
                    arguments={"session_id": state.session_id, "rating": rating, "comments": user_text},
                )
            )
            res = record_customer_feedback(session_id=state.session_id, rating=rating, comments=user_text)
            tool_results.append(ToolResult(tool_name="record_customer_feedback", result=res))

            if language == LanguageCode.HI:
                msg = f"आपकी प्रतिक्रिया और {rating} स्टार रेटिंग दर्ज कर ली गई है। धन्यवाद!"
            elif language == LanguageCode.HINGLISH:
                msg = f"Aapka feedback record kar liya gaya hai (Rating: {rating}/5). Humse judne ke liye dhanyawaad!"
            else:
                msg = f"Thank you for your feedback! Your {rating}-star rating has been successfully recorded."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        else:
            # Dealer details lookup
            tool_calls.append(ToolCall(tool_name="get_dealer_details", arguments={"dealer_code": "DLR-901"}))
            res = get_dealer_details(dealer_code="DLR-901")
            tool_results.append(ToolResult(tool_name="get_dealer_details", result=res))

            if language == LanguageCode.HI:
                msg = f"आपका अधिकृत डीलर '{res['name']}' है ({res.get('city', '')})। सर्विस मैनेजर {res.get('service_manager', '')} हैं, फोन: {res.get('phone', '')}।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Aapka authorized dealer '{res['name']}' ({res.get('city', '')}) hai. Service Manager {res.get('service_manager', '')} hain (Phone: {res.get('phone', '')})."
            else:
                msg = f"Your authorized dealer is {res['name']} in {res.get('city', '')}, managed by {res.get('service_manager', '')} (Phone: {res.get('phone', '')})."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
