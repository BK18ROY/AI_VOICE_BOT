"""Deterministic Mock LLM Provider simulating Gemini 2.5 Flash."""

import asyncio
from typing import AsyncGenerator, Dict, List, Optional
from app.schemas.conversation import LanguageCode


class MockLLMProvider:
    """Simulates Gemini 2.5 Flash with streaming tokens and multilingual responses."""

    def __init__(self, default_response: Optional[str] = None):
        self.default_response = default_response
        self._canned_replies: Dict[str, str] = {
            "warranty": "Your product with serial SN-5521 has an active warranty valid through November 2027.",
            "emi": "Your next monthly EMI installment is 24,500 rupees, due on October 5th. Auto-debit is active.",
            "loan": "Your auto loan has an outstanding principal balance of 485,000 rupees. 36 of 60 installments are completed.",
            "roadside": "Emergency assistance has been dispatched. QuickRescue Unit 4 is en route with an estimated arrival of 22 minutes.",
            "dealer": "Your vehicle is in the Quality Inspection stage at Apex Motors. It will be ready by 5:30 PM today.",
            "hindi": "आपकी गाड़ी का वारंटी स्टेटस सक्रिय है और सहायता वैन रवाना कर दी गई है।",
            "hinglish": "Aapki car ka service inspection chal raha hai aur shaam 5:30 tak ready ho jayegi.",
        }

    def _select_response(self, user_prompt: str) -> str:
        if self.default_response:
            return self.default_response
        p = user_prompt.lower()
        if any(w in p for w in ["warranty", "guarantee"]):
            return self._canned_replies["warranty"]
        if any(w in p for w in ["emi", "installment"]):
            return self._canned_replies["emi"]
        if any(w in p for w in ["loan", "balance"]):
            return self._canned_replies["loan"]
        if any(w in p for w in ["breakdown", "puncture", "accident", "emergency", "tow", "roadside"]):
            return self._canned_replies["roadside"]
        if any(w in p for w in ["dealer", "job card", "service"]):
            return self._canned_replies["dealer"]
        if any(w in p for w in ["hindi mein", "hindi me", "गाड़ी", "नमस्ते"]):
            return self._canned_replies["hindi"]
        if any(w in p for w in ["batao", "karna hai", "kar do", "theek"]):
            return self._canned_replies["hinglish"]
        return "Thank you for contacting customer support. I have checked your account details and everything is in order."

    async def generate_stream(
        self,
        prompt: str,
        history: Optional[List[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream response word-by-word with realistic low latency."""
        # Simulated TTFT (Time To First Token) ~40ms
        await asyncio.sleep(0.04)

        full_reply = self._select_response(prompt)
        words = full_reply.split(" ")

        for idx, word in enumerate(words):
            token = word + (" " if idx < len(words) - 1 else "")
            yield token
            # Inter-token streaming interval
            await asyncio.sleep(0.015)

    async def generate_text(
        self,
        prompt: str,
        history: Optional[List[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Non-streaming generation."""
        await asyncio.sleep(0.05)
        return self._select_response(prompt)

    async def is_ready(self) -> bool:
        return True
