"""Unit tests for Gemini LLM provider and Mock LLM processor."""

import pytest
from app.providers.llm.gemini_provider import GeminiProvider
from app.providers.llm.mock_llm import MockLLMProvider


@pytest.mark.asyncio
async def test_mock_llm_canned_responses():
    """Verify that MockLLM routes to contextual support replies."""
    llm = MockLLMProvider()

    res_warranty = await llm.generate_text("Can you check my warranty status?")
    assert "warranty" in res_warranty.lower()

    res_loan = await llm.generate_text("What is my EMI balance?")
    assert "emi" in res_loan.lower() or "installment" in res_loan.lower()

    res_roadside = await llm.generate_text("I have a tire puncture and car breakdown on the highway")
    assert "assistance" in res_roadside.lower() or "emergency" in res_roadside.lower()

    res_hindi = await llm.generate_text("नमस्ते, हिंदी में बताओ")
    assert "वारंटी" in res_hindi or "सहायता" in res_hindi


@pytest.mark.asyncio
async def test_mock_llm_streaming():
    """Verify that MockLLM streams tokens asynchronously."""
    llm = MockLLMProvider()
    tokens = []
    async for token in llm.generate_stream("Please tell me about my car loan"):
        tokens.append(token)

    assert len(tokens) > 3
    full_sentence = "".join(tokens)
    assert len(full_sentence) > 10


@pytest.mark.asyncio
async def test_gemini_fallback_when_uncredentialed():
    """Verify that GeminiProvider gracefully falls back to mock when no API key is provided."""
    provider = GeminiProvider(api_key=None)
    assert not provider.has_credentials()

    tokens = []
    async for token in provider.generate_stream("Check warranty for SN-5521"):
        tokens.append(token)

    assert len(tokens) > 0
    full_text = "".join(tokens)
    assert "warranty" in full_text.lower()


@pytest.mark.asyncio
async def test_gemini_circuit_breaker_behavior():
    """Verify that circuit breaker prevents requests when threshold tripped."""
    provider = GeminiProvider(api_key="fake-key-for-test")
    # Trip circuit breaker
    provider.circuit_breaker.record_failure(Exception("Network error 1"))
    provider.circuit_breaker.record_failure(Exception("Network error 2"))
    provider.circuit_breaker.record_failure(Exception("Network error 3"))

    assert provider.circuit_breaker.can_execute() is False

    # Should transparently yield from fallback provider
    tokens = []
    async for token in provider.generate_stream("Where is nearest dealer?"):
        tokens.append(token)

    assert len(tokens) > 0
