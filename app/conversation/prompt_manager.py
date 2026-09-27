"""Dynamic system and conversational prompt generator for Gemini 2.5 Flash."""

from typing import List, Optional
from app.schemas.conversation import ConversationState, ConversationTurn, LanguageCode, MessageRole

BASE_SYSTEM_PROMPT = """You are an intelligent, empathetic, real-time voice customer support assistant for an automotive and vehicle services company.
You are interacting with callers over a telephone/voice channel.

VOICE GUIDELINES:
1. Speak concisely in 1 to 3 clear, natural spoken sentences. Avoid overly long replies or monologues.
2. NEVER use markdown symbols like bold asterisks (**word**), bullet points, tables, or numbered lists because these will be spoken aloud by a Text-to-Speech engine.
3. Pronounce numbers, dates, and amounts clearly.
4. Always respond in the target language requested by the caller:
   - For English: Speak natural, polite conversational English.
   - For Hindi (हिंदी): Speak respectful conversational Hindi using Devanagari.
   - For Hinglish: Speak fluent, friendly Romanized Hindi-English mix as commonly spoken in India.
5. If the caller asks to switch languages (e.g. "Hindi mein batao" or "Speak in English"), immediately switch without hesitation.
6. When resolving roadside emergencies, remain calm, reassuring, and prioritize safety first.
"""

LANGUAGE_INSTRUCTIONS = {
    LanguageCode.EN: "Target Language: English. Keep phrasing polite, professional, and clear.",
    LanguageCode.HI: "Target Language: Hindi (हिंदी). शुद्ध और विनम्र हिंदी में उत्तर दें।",
    LanguageCode.HINGLISH: "Target Language: Hinglish (Romanized Hindi). Use natural conversational Hinglish words like 'Aapki car', 'Service status check kar diya hai'.",
}


class PromptManager:
    """Constructs tailored system prompts and message payloads for LLM invocation."""

    @staticmethod
    def build_system_prompt(state: ConversationState, language: LanguageCode) -> str:
        """Compose the dynamic system prompt with context."""
        parts = [BASE_SYSTEM_PROMPT]
        parts.append(LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS[LanguageCode.EN]))

        if state.active_workflow:
            parts.append(f"Active Workflow Context: {state.active_workflow}")
        if state.caller_id:
            parts.append(f"Caller Identifier: {state.caller_id}")

        return "\n\n".join(parts)

    @staticmethod
    def format_history_for_llm(history: List[ConversationTurn], max_turns: int = 6) -> List[dict]:
        """Convert recent turn history into standard chat messages."""
        recent_turns = history[-max_turns:]
        messages = []
        for t in recent_turns:
            role = "user" if t.role == MessageRole.USER else "assistant"
            messages.append({"role": role, "content": t.content})
        return messages
