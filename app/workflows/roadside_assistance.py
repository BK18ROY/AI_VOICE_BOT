"""Emergency roadside assistance workflow."""

import re
from app.schemas.conversation import ConversationState, IntentType, LanguageCode, ToolCall, ToolResult
from app.tools.roadside_tools import (
    create_assistance_request,
    get_assistance_eta,
    get_nearest_service_location,
    get_vehicle_status,
)
from app.workflows.base_workflow import BaseWorkflow, WorkflowResult


class RoadsideAssistanceWorkflow(BaseWorkflow):
    """Workflow handling breakdowns, emergency dispatch, and roadside telematics."""

    def __init__(self):
        super().__init__(
            name="roadside_assistance",
            intent=IntentType.ROADSIDE_ASSISTANCE,
            description="Manages vehicle breakdowns, emergency roadside dispatch, tow trucks, and ETAs.",
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

        if any(w in text_lower for w in ["eta", "track", "where", "kahan", "status", "kitni der"]):
            tool_calls.append(ToolCall(tool_name="get_assistance_eta", arguments={"request_id": "RSA-1001"}))
            res = get_assistance_eta(request_id="RSA-1001")
            tool_results.append(ToolResult(tool_name="get_assistance_eta", result=res))

            if language == LanguageCode.HI:
                msg = f"आपकी सहायता गाड़ी रास्ते में है और लगभग {res['estimated_arrival_minutes']} मिनट में पहुंचेगी (दूरी {res['current_distance_km']} किमी)।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Aapka roadside rescue unit raste mein hai aur lagbhag {res['estimated_arrival_minutes']} minutes mein pahunch jayega."
            else:
                msg = f"Your rescue unit is on the way ({res['current_distance_km']} km away) with an estimated arrival in {res['estimated_arrival_minutes']} minutes."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        elif any(w in text_lower for w in ["diagnose", "telematics", "engine", "battery", "light", "sensor"]):
            tool_calls.append(ToolCall(tool_name="get_vehicle_status", arguments={"vehicle_id": "VEH-3321"}))
            res = get_vehicle_status(vehicle_id="VEH-3321")
            tool_results.append(ToolResult(tool_name="get_vehicle_status", result=res))

            if language == LanguageCode.HI:
                msg = f"वाहन टेलीमैटिक्स से अलर्ट मिला है: {res['critical_alert']}। बैटरी वोल्टेज {res['battery_voltage']} सामान्य है।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Gadi ke sensors se alert mila hai: {res['critical_alert']}। Battery voltage {res['battery_voltage']} theek hai."
            else:
                msg = f"Vehicle telematics check complete: {res['critical_alert']}. Battery voltage is {res['battery_voltage']}."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        else:
            # Emergency dispatch
            issue = "puncture / flat tire" if "tire" in text_lower or "puncture" in text_lower else "general breakdown"
            location = "Current Highway Location"
            tool_calls.append(
                ToolCall(
                    tool_name="create_assistance_request",
                    arguments={"issue_type": issue, "location": location, "contact_number": "9876543210"},
                )
            )
            res = create_assistance_request(issue_type=issue, location=location, contact_number="9876543210")
            tool_results.append(ToolResult(tool_name="create_assistance_request", result=res))

            if language == LanguageCode.HI:
                msg = f"चिंता मत कीजिये, आपकी इमरजेंसी सहायता टिकट {res['request_id']} दर्ज कर दी गई है। पेट्रोल वैन रवाना हो चुकी है और {res['estimated_arrival_minutes']} मिनट में पहुंचेगी।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Fikar na karein, aapki emergency request {res['request_id']} create ho gayi hai. Rescue unit nikal chuka hai aur {res['estimated_arrival_minutes']} mins mein pahunch jayega."
            else:
                msg = f"Emergency assistance request {res['request_id']} has been dispatched. Technician {res['technician_name']} is en route with an ETA of {res['estimated_arrival_minutes']} minutes."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
