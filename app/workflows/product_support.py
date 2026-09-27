"""Product support workflow implementation."""

import re
from app.schemas.conversation import ConversationState, IntentType, LanguageCode, ToolCall, ToolResult
from app.tools.product_tools import (
    get_product_availability,
    get_product_information,
    get_product_order_status,
    get_product_warranty,
)
from app.workflows.base_workflow import BaseWorkflow, WorkflowResult


class ProductSupportWorkflow(BaseWorkflow):
    """Workflow handling product specifications, availability, order tracking, and warranty."""

    def __init__(self):
        super().__init__(
            name="product_support",
            intent=IntentType.PRODUCT_SUPPORT,
            description="Handles product specs, stock, shipment status, and warranty inquiries.",
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

        if any(w in text_lower for w in ["warranty", "guarantee", "vaaranty", "vaarante"]):
            # Extract serial number or use default
            sn_match = re.search(r"sn[-\s]?\d+", text_lower)
            sn = sn_match.group(0).upper().replace(" ", "") if sn_match else "SN-5521"

            tool_calls.append(ToolCall(tool_name="get_product_warranty", arguments={"serial_number": sn}))
            res = get_product_warranty(serial_number=sn)
            tool_results.append(ToolResult(tool_name="get_product_warranty", result=res))

            if language == LanguageCode.HI:
                msg = f"आपकी डिवाइस (सीरियल {sn}) की वारंटी {res['valid_until']} तक सक्रिय है। यह मैन्युफैक्चरर वारंटी के तहत कवर्ड है।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Aapki device (serial {sn}) ki warranty {res['valid_until']} tak valid aur active hai. Yeh full coverage mein aati hai."
            else:
                msg = f"Your product with serial {sn} has an active warranty valid through {res['valid_until']} with full coverage."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        elif any(w in text_lower for w in ["order", "dispatch", "delivery", "track", "parcel"]):
            ord_match = re.search(r"ord[-\s]?\d+", text_lower)
            ord_id = ord_match.group(0).upper().replace(" ", "") if ord_match else "ORD-9982"

            tool_calls.append(ToolCall(tool_name="get_product_order_status", arguments={"order_id": ord_id}))
            res = get_product_order_status(order_id=ord_id)
            tool_results.append(ToolResult(tool_name="get_product_order_status", result=res))

            if language == LanguageCode.HI:
                msg = f"आपका ऑर्डर {ord_id} डिलीवरी के लिए निकल चुका है। यह {res['expected_delivery']} तक पहुंचेगा।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Aapka order {ord_id} out for delivery hai aur {res['expected_delivery']} deliver ho jayega."
            else:
                msg = f"Order {ord_id} is out for delivery with {res['carrier']} and expected {res['expected_delivery']}."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        elif any(w in text_lower for w in ["stock", "available", "availability", "buy", "khareed"]):
            tool_calls.append(ToolCall(tool_name="get_product_availability", arguments={"product_id": "P100", "pincode": "110001"}))
            res = get_product_availability(product_id="P100", pincode="110001")
            tool_results.append(ToolResult(tool_name="get_product_availability", result=res))

            if language == LanguageCode.HI:
                msg = f"यह प्रोडक्ट आपके पिनकोड पर उपलब्ध है। स्टॉक में {res['stock_count']} यूनिट्स हैं और डिलीवरी 2 दिनों में संभव है।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Haan ji, yeh product available hai. Stock mein {res['stock_count']} units hain aur 2 din mein delivery ho jayegi."
            else:
                msg = f"Good news, the product is in stock ({res['stock_count']} units available) and can be delivered within 2 business days."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        else:
            # Default product specs
            tool_calls.append(ToolCall(tool_name="get_product_information", arguments={"product_id": "P100"}))
            res = get_product_information(product_id="P100")
            tool_results.append(ToolResult(tool_name="get_product_information", result=res))

            if language == LanguageCode.HI:
                msg = f"यह {res['name']} है, जिसमें वायरलेस कारप्ले और वॉयस नेविगेशन जैसी सुविधाएं शामिल हैं।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Yeh {res['name']} model {res.get('model', '')} hai, jisme wireless CarPlay aur voice navigation features hain."
            else:
                msg = f"This is the {res['name']} featuring {', '.join(res.get('features', []))}."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
