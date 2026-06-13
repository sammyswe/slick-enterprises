"""Provider-agnostic LLM layer.

Callers depend on `ModelProvider` and never on a vendor SDK directly. Adding OpenAI
or local models later means adding a provider, not rewriting callers. Every call
returns token usage so the cost-controller can record a `CostEvent`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .config import Settings, get_settings
from .pricing import estimate_cost


@dataclass
class CompletionRequest:
    prompt: str
    system: str = ""
    model: str | None = None  # None => use the cheap model
    max_tokens: int = 1024
    purpose: str = ""  # e.g. "clarifying-questions", "code", "review"


@dataclass
class CompletionResult:
    text: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    estimated_cost: float = 0.0
    mock: bool = False
    meta: dict = field(default_factory=dict)


class ModelProvider(Protocol):
    name: str

    async def complete(self, req: CompletionRequest) -> CompletionResult: ...


def _approx_tokens(text: str) -> int:
    # Rough heuristic (~4 chars/token) good enough for mock accounting.
    return max(1, len(text) // 4)


class MockProvider:
    """Deterministic, zero-cost provider used when MODEL_MOCK_MODE=true."""

    name = "mock"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def complete(self, req: CompletionRequest) -> CompletionResult:
        model = req.model or self.settings.model_cheap
        text = self._respond(req)
        return CompletionResult(
            text=text,
            model=model,
            provider=self.name,
            tokens_in=_approx_tokens(req.system + req.prompt),
            tokens_out=_approx_tokens(text),
            estimated_cost=0.0,
            mock=True,
        )

    @staticmethod
    def _respond(req: CompletionRequest) -> str:
        purpose = req.purpose or "general"
        if purpose == "clarifying-questions":
            return (
                "1. Who is the target customer?\n"
                "2. What is the single most important outcome?\n"
                "3. What data sources or integrations are required?\n"
                "4. What is the success metric for v1?\n"
                "5. Any hard constraints (budget, deadline, compliance)?"
            )
        if purpose == "summary":
            return "Mock summary: work proceeded through the autonomous loop and is on track."
        return f"[mock:{purpose}] {req.prompt[:160]}"


class AnthropicProvider:
    """Real Anthropic provider. Imported lazily so the SDK is optional."""

    name = "anthropic"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                import anthropic  # type: ignore
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "anthropic package not installed. Install with `pip install anthropic` "
                    "or set MODEL_MOCK_MODE=true."
                ) from exc
            self._client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    async def complete(self, req: CompletionRequest) -> CompletionResult:
        model = req.model or self.settings.model_cheap
        client = self._ensure_client()
        resp = await client.messages.create(
            model=model,
            max_tokens=req.max_tokens,
            system=req.system or "You are a helpful agent in Slick Enterprises HQ.",
            messages=[{"role": "user", "content": req.prompt}],
        )
        text = "".join(getattr(block, "text", "") for block in resp.content)
        tokens_in = getattr(resp.usage, "input_tokens", 0)
        tokens_out = getattr(resp.usage, "output_tokens", 0)
        return CompletionResult(
            text=text,
            model=model,
            provider=self.name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost=estimate_cost(model, tokens_in, tokens_out),
        )


def get_provider(settings: Settings | None = None) -> ModelProvider:
    """Return the configured provider (or the mock provider in mock mode)."""
    settings = settings or get_settings()
    if settings.model_mock_mode or not settings.anthropic_api_key:
        return MockProvider(settings)
    if settings.model_provider == "anthropic":
        return AnthropicProvider(settings)
    # Future: openai, ollama, vllm, llama.cpp providers.
    return MockProvider(settings)
