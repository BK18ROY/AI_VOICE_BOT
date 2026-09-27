"""Unit tests for Language Detection and multilingual switching."""

import pytest
from app.conversation.language_detector import LanguageDetector
from app.schemas.conversation import LanguageCode


def test_english_detection():
    detector = LanguageDetector()
    lang, conf = detector.detect("Can you check the warranty status for my product?")
    assert lang == LanguageCode.EN
    assert conf >= 0.8


def test_hindi_devanagari_detection():
    detector = LanguageDetector()
    lang, conf = detector.detect("मेरी गाड़ी का ईएमआई स्टेटस क्या है?")
    assert lang == LanguageCode.HI
    assert conf >= 0.9


def test_hinglish_romanized_detection():
    detector = LanguageDetector()
    lang, conf = detector.detect("Mera gaadi ka loan status batao kripya")
    assert lang == LanguageCode.HINGLISH
    assert conf >= 0.7


def test_explicit_language_switch_directive():
    detector = LanguageDetector()

    # Current language is English, user asks for Hindi
    lang1, conf1 = detector.detect("Achha please Hindi mein batao", current_language=LanguageCode.EN)
    assert lang1 == LanguageCode.HI
    assert conf1 >= 0.95

    # Current language is Hindi, user asks for English
    lang2, conf2 = detector.detect("Now speak English please", current_language=LanguageCode.HI)
    assert lang2 == LanguageCode.EN
    assert conf2 >= 0.95

    # Switch to Hinglish
    lang3, conf3 = detector.detect("Hinglish me baat karo", current_language=LanguageCode.EN)
    assert lang3 == LanguageCode.HINGLISH


def test_empty_and_fallback_behavior():
    detector = LanguageDetector()
    lang, conf = detector.detect("", current_language=LanguageCode.HI)
    assert lang == LanguageCode.HI

    lang2, conf2 = detector.detect("12345", current_language=LanguageCode.EN)
    assert lang2 == LanguageCode.EN
