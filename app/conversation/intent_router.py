"""Intent routing module determining workflow path."""

from typing import Tuple
from app.schemas.conversation import IntentType


class IntentRouter:
    """Classifies user intent based on keyword cues and contextual history."""

    INTENT_KEYWORDS = {
        IntentType.ROADSIDE_ASSISTANCE: [
            "breakdown", "broken", "accident", "puncture", "flat tire", "tow", "towing",
            "emergency", "kharab", "patrol", "highway", "battery dead", "stuck", "assistance",
            "roadside", "rsa", "help me", "gaadi ruk gayi",
        ],
        IntentType.FINANCE_SUPPORT: [
            "emi", "loan", "payment", "installment", "interest", "bank", "account", "balance",
            "principal", "autopay", "nach", "due date", "paid", "debit", "kist", "kisht", "paisa",
        ],
        IntentType.PRODUCT_SUPPORT: [
            "warranty", "guarantee", "console", "infotainment", "product", "features", "stock",
            "availability", "order", "delivery", "specifications", "accessory", "manual",
        ],
        IntentType.DEALER_SUPPORT: [
            "dealer", "dealership", "workshop", "job card", "service center", "servicing",
            "repair", "inspection", "feedback", "rating", "manager", "mechanic",
        ],
        IntentType.GREETING: [
            "hello", "hi", "hey", "namaste", "good morning", "good evening", "kya haal hai",
            "kaise ho", "sun rahe ho",
        ],
    }

    def route(self, user_text: str, current_intent: IntentType = IntentType.GREETING) -> Tuple[IntentType, float]:
        """Classify user intent with confidence score [0.0, 1.0]."""
        if not user_text or not user_text.strip():
            return current_intent, 0.5

        text_lower = user_text.lower()
        scored_intents = []

        for intent, keywords in self.INTENT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > 0:
                score = min(0.5 + matches * 0.25, 0.99)
                scored_intents.append((intent, score))

        if scored_intents:
            scored_intents.sort(key=lambda x: x[1], reverse=True)
            return scored_intents[0]

        # If user is in middle of a conversation, retain previous intent unless greeting
        if current_intent not in (IntentType.GREETING, IntentType.FALLBACK):
            return current_intent, 0.6

        return IntentType.GENERAL_QUERY, 0.5
