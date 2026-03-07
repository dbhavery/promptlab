"""Model adapters for Ollama, Claude, and Gemini."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class ModelResponse:
    """Response from a model adapter."""

    text: str
    model: str
    latency_ms: float = 0.0
    error: str | None = None


class ModelAdapter(ABC):
    """Base class for model adapters."""

    @abstractmethod
    async def generate(self, prompt: str, user_input: str) -> ModelResponse:
        """Generate a response from the model.

        Args:
            prompt: The system prompt / instruction.
            user_input: The user's input message.

        Returns:
            A ModelResponse with the generated text.
        """


class OllamaAdapter(ModelAdapter):
    """Adapter for Ollama local models.

    Model string format: ``ollama/<model-name>``
    Example: ``ollama/qwen3:8b``
    """

    def __init__(self, model_name: str, base_url: str = "http://localhost:11434") -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    async def generate(self, prompt: str, user_input: str) -> ModelResponse:
        """Call the Ollama /api/generate endpoint."""
        import time

        url = f"{self.base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self.model_name,
            "prompt": user_input,
            "system": prompt,
            "stream": False,
        }

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return ModelResponse(
                text="",
                model=f"ollama/{self.model_name}",
                latency_ms=elapsed,
                error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return ModelResponse(
                text="",
                model=f"ollama/{self.model_name}",
                latency_ms=elapsed,
                error=f"Connection error: {exc}",
            )

        elapsed = (time.perf_counter() - start) * 1000
        return ModelResponse(
            text=data.get("response", ""),
            model=f"ollama/{self.model_name}",
            latency_ms=elapsed,
        )


class ClaudeAdapter(ModelAdapter):
    """Adapter for Anthropic Claude models.

    Model string format: ``claude/<model-id>``
    Example: ``claude/claude-sonnet-4-6``

    Requires the ``anthropic`` package (install with ``pip install promptlab[claude]``).
    """

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    async def generate(self, prompt: str, user_input: str) -> ModelResponse:
        """Call the Anthropic Messages API."""
        import time

        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            return ModelResponse(
                text="",
                model=f"claude/{self.model_id}",
                error="anthropic package not installed. Run: pip install promptlab[claude]",
            )

        client = AsyncAnthropic()
        start = time.perf_counter()
        try:
            message = await client.messages.create(
                model=self.model_id,
                max_tokens=1024,
                system=prompt,
                messages=[{"role": "user", "content": user_input}],
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return ModelResponse(
                text="",
                model=f"claude/{self.model_id}",
                latency_ms=elapsed,
                error=str(exc),
            )

        elapsed = (time.perf_counter() - start) * 1000
        text_parts = [
            block.text for block in message.content if hasattr(block, "text")
        ]
        return ModelResponse(
            text="".join(text_parts),
            model=f"claude/{self.model_id}",
            latency_ms=elapsed,
        )


class GeminiAdapter(ModelAdapter):
    """Adapter for Google Gemini models.

    Model string format: ``gemini/<model-id>``
    Example: ``gemini/gemini-2.5-flash``

    Requires the ``google-genai`` package (install with ``pip install promptlab[gemini]``).
    """

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    async def generate(self, prompt: str, user_input: str) -> ModelResponse:
        """Call the Google Generative AI API."""
        import time

        try:
            from google import genai
        except ImportError:
            return ModelResponse(
                text="",
                model=f"gemini/{self.model_id}",
                error="google-genai package not installed. Run: pip install promptlab[gemini]",
            )

        client = genai.Client()
        start = time.perf_counter()
        try:
            full_prompt = f"{prompt}\n\nUser: {user_input}"
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model_id,
                contents=full_prompt,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return ModelResponse(
                text="",
                model=f"gemini/{self.model_id}",
                latency_ms=elapsed,
                error=str(exc),
            )

        elapsed = (time.perf_counter() - start) * 1000
        return ModelResponse(
            text=response.text or "",
            model=f"gemini/{self.model_id}",
            latency_ms=elapsed,
        )


def create_adapter(model_string: str) -> ModelAdapter:
    """Create a model adapter from a model string.

    Supported formats:
        - ``ollama/<model-name>`` (e.g. ``ollama/qwen3:8b``)
        - ``claude/<model-id>`` (e.g. ``claude/claude-sonnet-4-6``)
        - ``gemini/<model-id>`` (e.g. ``gemini/gemini-2.5-flash``)

    Args:
        model_string: The model identifier string.

    Returns:
        An instance of the appropriate ModelAdapter subclass.

    Raises:
        ValueError: If the model string format is unrecognized.
    """
    if "/" not in model_string:
        raise ValueError(
            f"Invalid model string '{model_string}'. "
            "Expected format: 'provider/model-name' "
            "(e.g. 'ollama/qwen3:8b', 'claude/claude-sonnet-4-6')."
        )

    provider, model_name = model_string.split("/", 1)
    provider = provider.lower().strip()

    if provider == "ollama":
        return OllamaAdapter(model_name)
    elif provider == "claude":
        return ClaudeAdapter(model_name)
    elif provider == "gemini":
        return GeminiAdapter(model_name)
    else:
        raise ValueError(
            f"Unknown model provider '{provider}'. "
            "Supported providers: ollama, claude, gemini."
        )
