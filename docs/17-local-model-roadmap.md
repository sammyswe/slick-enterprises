# 17 · Local Model Roadmap

v1 uses **cloud models** (Anthropic first). Local inference is a **future feature**,
documented here so the design stays ready for it.

## Why not local in v1

- The GMKtec M6 Ultra has **16 GB RAM** and an integrated GPU — fine for orchestration
  and web, but tight for capable LLM inference alongside the full stack.
- Cloud models give the best quality-per-effort while we build the factory itself.

## Design that keeps local models easy later

The LLM layer is **provider-agnostic** (`slick_shared/llm.py`):

```python
class ModelProvider(Protocol):
    async def complete(self, req: CompletionRequest) -> CompletionResult: ...

# v1: AnthropicProvider, MockProvider
# future: OpenAIProvider, OllamaProvider, vLLMProvider, LlamaCppProvider
```

Adding a local provider means implementing this interface and registering it — callers
(agents, orchestrator) don't change.

## Candidate local stacks (future)

| Option | Notes |
|--------|-------|
| **Ollama** | Easiest local serving; good for small/medium models |
| **llama.cpp** | CPU/quantized friendly; runs on modest hardware |
| **vLLM** | Higher throughput; needs more VRAM/RAM |

Quantized small models (e.g. 7–8B) can handle routing, clarifying questions, and
summaries — exactly the **cheap-model** tier.

## Hybrid routing (the target)

Route by task difficulty and privacy:

```
cheap / private / routing   ─► local model (Ollama/llama.cpp)
hard / architecture / code  ─► cloud model (Anthropic)
```

This cuts cost (local ≈ $0 marginal) and keeps sensitive context on the box.

## Hardware path

- Stay on cloud while on the 16 GB miniPC.
- For serious local inference, add RAM or a dedicated GPU box and point the
  `OllamaProvider`/`vLLMProvider` at it over the LAN.

## Prerequisites before enabling local

1. Provider implementation + pricing/usage accounting (local = $0 marginal, but log
   latency/tokens).
2. Quality evaluation harness (Evaluator agent) to decide local-vs-cloud per task.
3. Resource guardrails so local inference never starves Postgres/Redis/UI.

Until then, keep `MODEL_PROVIDER=anthropic` and `MODEL_MOCK_MODE` as appropriate.
