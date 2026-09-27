"""Language detection and dynamic switching across English, Hindi, and Hinglish."""

import re
from typing import Tuple
from app.schemas.conversation import LanguageCode

# Common Romanized Hindi / Hinglish tokens
HINGLISH_KEYWORDS = {
    "mera", "meri", "mere", "gaadi", "gadi", "batao", "bataiye", "karna", "karein",
    "hai", "hain", "kripya", "kar", "do", "kijiye", "achha", "accha", "theek",
    "mein", "me", "ka", "ki", "ke", "ko", "chahiye", "nahi", "nahin", "kya", "kyon",
    "kab", "kahan", "kitna", "kitni", "kaise", "haan", "sir", "madam", "paise", "rupaye",
    "kharab", "dhanyawaad", "shukriya", "jaldi", "madad", "madat", "bolo", "boliye",
}

LANGUAGE_SWITCH_DIRECTIVES = [
    (r"\b(hindi|hindi mein|hindi me|shuddh hindi)\b", LanguageCode.HI),
    (r"\b(hinglish|roman hindi|hinglish me|hinglish mein)\b", LanguageCode.HINGLISH),
    (r"\b(english|english please|speak english|in english)\b", LanguageCode.EN),
]


class LanguageDetector:
    """Detects primary language and identifies mid-conversation explicit language switches."""

    def __init__(self, default_language: LanguageCode = LanguageCode.EN):
        self.default_language = default_language

    def detect(self, text: str, current_language: LanguageCode = LanguageCode.EN) -> Tuple[LanguageCode, float]:
        """Detect language with confidence score [0.0, 1.0]."""
        if not text or not text.strip():
            return current_language, 1.0

        cleaned_text = text.strip()
        lower_text = cleaned_text.lower()

        # 1. Check for explicit mid-dialogue switch commands
        for pattern, target_lang in LANGUAGE_SWITCH_DIRECTIVES:
            if re.search(pattern, lower_text):
                return target_lang, 0.98

        # 2. Check for Devanagari Unicode script range [\u0900-\u097F]
        devanagari_chars = len(re.findall(r"[\u0900-\u097F]", cleaned_text))
        total_chars = len(re.findall(r"\w", cleaned_text))

        if total_chars > 0 and (devanagari_chars / total_chars) > 0.3:
            return LanguageCode.HI, 0.95

        # 3. Analyze words for Romanized Hindi / Hinglish tokens
        words = re.findall(r"\b[a-zA-Z]+\b", lower_text)
        if not words:
            return current_language, 0.5

        hinglish_count = sum(1 for w in words if w in HINGLISH_KEYWORDS)
        hinglish_ratio = hinglish_count / len(words)

        if hinglish_ratio >= 0.25:
            return LanguageCode.HINGLISH, min(0.6 + hinglish_ratio * 0.4, 0.95)

        # 4. English fallback
        if hinglish_count == 0 and any(w in lower_text for w in ["the", "is", "my", "car", "status", "please", "can", "what", "where"]):
            return LanguageCode.EN, 0.9

        return current_language, 0.7
