"""Finance and auto-loan support workflow."""

from app.schemas.conversation import ConversationState, IntentType, LanguageCode, ToolCall, ToolResult
from app.tools.finance_tools import (
    get_account_summary,
    get_emi_details,
    get_loan_status,
    get_payment_status,
)
from app.workflows.base_workflow import BaseWorkflow, WorkflowResult


class FinanceSupportWorkflow(BaseWorkflow):
    """Workflow handling EMI inquiries, loan balances, and auto-debit payments."""

    def __init__(self):
        super().__init__(
            name="finance_support",
            intent=IntentType.FINANCE_SUPPORT,
            description="Assists with vehicle loan status, EMI schedules, and payment verification.",
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

        if any(w in text_lower for w in ["emi", "installment", "kist", "kisht", "due"]):
            tool_calls.append(ToolCall(tool_name="get_emi_details", arguments={"account_id": "ACC-101"}))
            res = get_emi_details(account_id="ACC-101")
            tool_results.append(ToolResult(tool_name="get_emi_details", result=res))

            if language == LanguageCode.HI:
                msg = f"आपकी आगामी EMI राशि ₹{res['monthly_emi_amount_inr']:,.2f} है, जो {res['next_due_date']} को देय है। आपका ऑटो-पे सक्रिय है।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Aapki agli EMI amount ₹{res['monthly_emi_amount_inr']:,.2f} hai aur due date {res['next_due_date']} hai. Auto-pay successfully enabled hai."
            else:
                msg = f"Your next monthly EMI installment is ₹{res['monthly_emi_amount_inr']:,.2f}, due on {res['next_due_date']}. Auto-debit is active."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        elif any(w in text_lower for w in ["loan", "outstanding", "balance", "principal", "rin"]):
            tool_calls.append(ToolCall(tool_name="get_loan_status", arguments={"loan_account_number": "LN-4412"}))
            res = get_loan_status(loan_account_number="LN-4412")
            tool_results.append(ToolResult(tool_name="get_loan_status", result=res))

            if language == LanguageCode.HI:
                msg = f"आपके लोन खाते (LN-4412) का शेष मूलधन ₹{res['principal_outstanding_inr']:,.2f} है। 60 में से 36 किस्तें पूरी हो चुकी हैं।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Aapke car loan ka outstanding principal ₹{res['principal_outstanding_inr']:,.2f} bacha hai. 36 out of 60 months complete ho chuke hain."
            else:
                msg = f"Your loan account LN-4412 has a principal balance of ₹{res['principal_outstanding_inr']:,.2f}. 36 of 60 months have been paid."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        elif any(w in text_lower for w in ["payment", "paid", "transaction", "debit", "clear", "paisa"]):
            tool_calls.append(ToolCall(tool_name="get_payment_status", arguments={"transaction_id": "TXN-8812"}))
            res = get_payment_status(transaction_id="TXN-8812")
            tool_results.append(ToolResult(tool_name="get_payment_status", result=res))

            if language == LanguageCode.HI:
                msg = f"आपका अंतिम भुगतान ₹{res['amount_inr']:,.2f} का {res['payment_date']} को सफलतापूर्वक पूरा हो गया था।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Aapka last payment ₹{res['amount_inr']:,.2f} ka {res['payment_date']} ko successfully clear ho gaya hai."
            else:
                msg = f"Your last payment of ₹{res['amount_inr']:,.2f} cleared successfully on {res['payment_date']} via auto-debit."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        else:
            tool_calls.append(ToolCall(tool_name="get_account_summary", arguments={"customer_id": "CUST-007"}))
            res = get_account_summary(customer_id="CUST-007")
            tool_results.append(ToolResult(tool_name="get_account_summary", result=res))

            if language == LanguageCode.HI:
                msg = f"नमस्ते {res['customer_name']}, आपके पास 1 सक्रिय ऑटो लोन है और ₹{res['pre_approved_topup_inr']:,.2f} का प्री-एप्रूव्ड ऑफर उपलब्ध है।"
            elif language == LanguageCode.HINGLISH:
                msg = f"Hi {res['customer_name']}, aapke account mein 1 active loan hai aur ₹{res['pre_approved_topup_inr']:,.2f} ka pre-approved top-up available hai."
            else:
                msg = f"Hello {res['customer_name']}, your finance account is in prime standing with 1 active auto loan and a pre-approved top-up offer."

            return WorkflowResult(
                workflow_name=self.name,
                intent=self.intent,
                response_text=msg,
                language=language,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
