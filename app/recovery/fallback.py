"""Fallback responses and error message generators across English, Hindi, and Hinglish."""

from typing import Dict
from app.schemas.conversation import LanguageCode

FALLBACK_MESSAGES: Dict[str, Dict[LanguageCode, str]] = {
    "unintelligible": {
        LanguageCode.EN: "I'm sorry, I couldn't quite hear you. Could you please repeat that?",
        LanguageCode.HI: "माफ़ कीजिये, मैं ठीक से सुन नहीं पाया। क्या आप दोबारा कह सकते हैं?",
        LanguageCode.HINGLISH: "Sorry, main theek se sun nahi paya. Kya aap please repeat kar sakte hain?",
    },
    "llm_error": {
        LanguageCode.EN: "I am experiencing a momentary network delay. Let me check that for you right now.",
        LanguageCode.HI: "मुझे कनेक्ट करने में थोड़ी परेशानी आ रही है। कृपया एक क्षण प्रतीक्षा करें।",
        LanguageCode.HINGLISH: "Thoda network issue aa raha hai. Main turant check karke batata hoon.",
    },
    "service_error": {
        LanguageCode.EN: "I apologize, our backend system is taking longer than expected. How else may I assist you?",
        LanguageCode.HI: "मुझे खेद है, हमारे सिस्टम से संपर्क नहीं हो पा रहा है। क्या मैं किसी और चीज़ में मदद कर सकता हूँ?",
        LanguageCode.HINGLISH: "Mujhe khed hai, system thoda slow chal raha hai. Kya main kisi aur cheez mein help kar sakta hoon?",
    },
    "empty_transcript": {
        LanguageCode.EN: "Hello! Are you still there? Please let me know how I can help you.",
        LanguageCode.HI: "नमस्ते! क्या आप सुन पा रहे हैं? कृपया बताइए मैं आपकी क्या मदद करूँ।",
        LanguageCode.HINGLISH: "Hello! Kya aap line pe hain? Please batayein main aapki kya help kar sakta hoon.",
    },
    "handoff": {
        LanguageCode.EN: "I am connecting you with a human customer support specialist. Please stay on the line.",
        LanguageCode.HI: "मैं आपकी कॉल हमारे कस्टमर केयर एग्जीक्यूटिव को ट्रांसफर कर रहा हूँ। कृपया लाइन पर बने रहें।",
        LanguageCode.HINGLISH: "Main aapki call customer support agent ko connect kar raha hoon. Please line par bane rahein.",
    },
}


def get_fallback_response(
    error_key: str = "service_error",
    language: LanguageCode = LanguageCode.EN,
) -> str:
    """Retrieve localized fallback message."""
    messages = FALLBACK_MESSAGES.get(error_key, FALLBACK_MESSAGES["service_error"])
    return messages.get(language, messages[LanguageCode.EN])
