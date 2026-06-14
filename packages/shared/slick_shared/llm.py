"""Provider-agnostic LLM layer.

Callers depend on `ModelProvider` and never on a vendor SDK directly. Adding OpenAI
or local models later means adding a provider, not rewriting callers.

Cost handling differs by provider:
  * Anthropic returns token usage; we estimate a per-call dollar cost.
  * Cursor (Composer) bills against your subscription/request pool and returns no
    token counts. We record run metadata for usage tracking and report $0 per call.
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
    mcp_servers: list[dict] = field(default_factory=list)


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


class CursorProvider:
    """Cursor SDK provider — runs Composer, the same agent that powers the IDE.

    Unlike a chat-completion API, the Cursor SDK drives a full coding agent. We use
    it as a completion source here: non-coding purposes run in ``plan`` mode (no file
    edits) while coding purposes run in ``agent`` mode against ``cursor_workspace_dir``.

    Billing note: the SDK does NOT return token counts or per-call dollar cost. Runs
    bill against your Cursor subscription / request pool and show up in the Cursor
    usage dashboard under the "SDK" tag. We therefore report ``estimated_cost=0.0``
    and record run metadata (id, duration, status) in ``meta`` for usage tracking.
    """

    name = "cursor"
    # Purposes that should EDIT files run in Composer "agent" mode. Everything else
    # (planning, evaluation, clarifying questions, naming, summaries) runs in "ask"
    # mode — a read-only chat that returns the answer INLINE. Plan mode is avoided
    # because it forces the CreatePlan tool and returns only status chatter, not text.
    _AGENT_PURPOSES = {"code", "coding", "implement", "fix"}

    def __init__(self, settings: Settings):
        self.settings = settings

    def _select_model(self, req: CompletionRequest) -> str:
        if req.model and (req.model.startswith("composer") or req.model == "auto"):
            return req.model
        smart = req.purpose in {"code", "coding", "review", "architecture", "plan"}
        return self.settings.cursor_model_smart if smart else self.settings.cursor_model_cheap

    async def complete(self, req: CompletionRequest) -> CompletionResult:
        try:
            from cursor_sdk import AsyncClient, LocalAgentOptions, SendOptions  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "cursor-sdk not installed. Install with `pip install cursor-sdk` "
                "or set MODEL_MOCK_MODE=true."
            ) from exc

        if not self.settings.cursor_api_key:  # pragma: no cover
            raise RuntimeError(
                "CURSOR_API_KEY is empty. Mint one at "
                "https://cursor.com/dashboard/integrations."
            )

        model = self._select_model(req)
        cwd = self.settings.cursor_workspace_dir
        mode = "agent" if req.purpose in self._AGENT_PURPOSES else "ask"
        message = f"{req.system}\n\n{req.prompt}".strip() if req.system else req.prompt

        async with await AsyncClient.launch_bridge(workspace=cwd) as client:
            async with await client.agents.create(
                model=model,
                api_key=self.settings.cursor_api_key,
                local=LocalAgentOptions(cwd=cwd),
            ) as agent:
                send_opts: dict = {"mode": mode}
                if req.mcp_servers:
                    send_opts["mcp_servers"] = req.mcp_servers
                run = await agent.send(message, SendOptions(**send_opts))
                result = await run.wait()
                text = (getattr(result, "result", None) or await run.text() or "").strip()

        return CompletionResult(
            text=text,
            model=model,
            provider=self.name,
            tokens_in=_approx_tokens(req.system + req.prompt),
            tokens_out=_approx_tokens(text),
            estimated_cost=0.0,  # billed to the Cursor subscription, not per-call
            meta={
                "billed_to": "cursor-subscription",
                "cursor_run_id": getattr(result, "id", ""),
                "duration_ms": getattr(result, "duration_ms", 0),
                "status": getattr(result, "status", ""),
                "runtime": self.settings.cursor_runtime,
                "mode": mode,
            },
        )


def get_provider(settings: Settings | None = None) -> ModelProvider:
    """Return the configured provider (or the mock provider when unconfigured)."""
    settings = settings or get_settings()
    if settings.model_mock_mode:
        return MockProvider(settings)
    if settings.model_provider == "cursor":
        if not settings.cursor_api_key:
            return MockProvider(settings)
        return CursorProvider(settings)
    if settings.model_provider == "anthropic":
        if not settings.anthropic_api_key:
            return MockProvider(settings)
        return AnthropicProvider(settings)
    # Future: openai, ollama, vllm, llama.cpp providers.
    return MockProvider(settings)
