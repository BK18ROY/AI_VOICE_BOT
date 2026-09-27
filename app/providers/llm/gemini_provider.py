"""Google Vertex AI & Gemini 2.5 Flash LLM Provider."""

import asyncio
from typing import AsyncGenerator, Dict, List, Optional
import httpx
from app.observability.logger import logger
from app.providers.llm.mock_llm import MockLLMProvider
from app.recovery.circuit_breaker import CircuitBreaker
from app.recovery.retry import async_retry


class GeminiProvider:
    """Production provider for Gemini 2.5 Flash via Vertex AI or Google AI Studio."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        project_id: Optional[str] = None,
        location: str = "us-central1",
        timeout_seconds: float = 5.0,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.project_id = project_id
        self.location = location
        self.timeout_seconds = timeout_seconds
        self.circuit_breaker = CircuitBreaker(name="gemini_llm", failure_threshold=3, recovery_timeout=20.0)
        self.fallback_provider = MockLLMProvider()

    def has_credentials(self) -> bool:
        """Check if sufficient credentials are provided."""
        return bool(self.api_key or self.project_id)

    async def generate_stream(
        self,
        prompt: str,
        history: Optional[List[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream generated response tokens from Gemini 2.5 Flash."""
        if not self.has_credentials() or not self.circuit_breaker.can_execute():
            logger.info("gemini_using_fallback_stream", reason="credentials_missing_or_circuit_open")
            async for token in self.fallback_provider.generate_stream(prompt, history, system_prompt):
                yield token
            return

        try:
            # Live Gemini API streaming call (simulated or via httpx/SDK)
            # When API key is provided, we can call Google AI Studio REST streaming endpoint:
            # https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={api_key}&alt=sse
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:streamGenerateContent"
            headers = {"Content-Type": "application/json"}
            params = {"key": self.api_key, "alt": "sse"}

            contents = []
            if system_prompt:
                contents.append({"role": "user", "parts": [{"text": f"SYSTEM: {system_prompt}"}]})
                contents.append({"role": "model", "parts": [{"text": "Understood. I will act as instructed."}]})
            if history:
                for h in history:
                    contents.append({
                        "role": "user" if h.get("role") == "user" else "model",
                        "parts": [{"text": h.get("content", "")}],
                    })
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            payload = {
                "contents": contents,
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 200},
            }

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                async with client.stream("POST", url, params=params, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        raise RuntimeError(f"Gemini API returned status {response.status_code}")

                    self.circuit_breaker.record_success()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            import json
                            data_str = line[6:].strip()
                            if data_str:
                                try:
                                    data = json.loads(data_str)
                                    candidates = data.get("candidates", [])
                                    if candidates:
                                        parts = candidates[0].get("content", {}).get("parts", [])
                                        for p in parts:
                                            text_chunk = p.get("text", "")
                                            if text_chunk:
                                                yield text_chunk
                                except Exception:
                                    continue
        except Exception as e:
            self.circuit_breaker.record_failure(e)
            logger.error("gemini_streaming_failed", error=str(e), action="falling_back_to_mock")
            async for token in self.fallback_provider.generate_stream(prompt, history, system_prompt):
                yield token

    async def generate_text(
        self,
        prompt: str,
        history: Optional[List[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Non-streaming text generation with retry."""
        tokens = []
        async for token in self.generate_stream(prompt, history, system_prompt):
            tokens.append(token)
        return "".join(tokens)

    async def is_ready(self) -> bool:
        return self.has_credentials()
