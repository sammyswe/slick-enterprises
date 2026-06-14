"""Shared prompt fragments for the self-building engine.

Loads the operating contract (the "self-prompting build loop" skill) and the
Constitution from the mounted repo so every planner / builder / evaluator run is
grounded in the same rules. Falls back to an embedded summary if the files are not
present (e.g. a service without the repo mounted), so prompts never crash.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .config import get_settings

_LOOP_SKILL_REL = "skills/global/self-prompting-build-loop.md"
_CONSTITUTION_REL = "docs/14-slick-enterprises-constitution.md"

_LOOP_FALLBACK = """\
Operating contract (self-prompting build loop):
plan -> decompose -> assign -> build in parallel -> execute tests -> evaluate ->
rework -> integrate -> repeat until acceptance criteria pass.
Quality bar (non-negotiable): no placeholders/stubs/TODOs in code meant to work;
wire every connection (imports, env, migrations, routes, startup); production-quality
error handling and types; prove each task with a real verification command; never
weaken the Constitution or commit secrets.
"""

_CONSTITUTION_FALLBACK = """\
Slick Enterprises HQ Constitution (summary): work autonomously but bounded; never
commit secrets; keep docs in sync with architecture; stay in scope; every change ships
with copy-pasteable verification steps.
"""


def _read_repo_file(rel_path: str, fallback: str) -> str:
    settings = get_settings()
    candidate = Path(settings.slick_repo_root) / rel_path
    try:
        text = candidate.read_text(encoding="utf-8").strip()
        return text or fallback
    except OSError:
        return fallback


@lru_cache
def build_loop_skill() -> str:
    """The self-prompting build loop, injected into every build/evaluate prompt."""
    return _read_repo_file(_LOOP_SKILL_REL, _LOOP_FALLBACK)


@lru_cache
def constitution_summary(max_chars: int = 2400) -> str:
    """Constitution text (trimmed) for grounding agent behaviour."""
    text = _read_repo_file(_CONSTITUTION_REL, _CONSTITUTION_FALLBACK)
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n... (truncated)"
    return text


def engine_system_preamble() -> str:
    """Common system-prompt preamble shared by builder and evaluator runs."""
    return (
        "You are a specialised agent inside Slick Enterprises HQ, infrastructure for "
        "businesses that run entirely on AI agent teams. You execute your assigned "
        "concern with real outputs — provision, operate, or verify as directed.\n\n"
        f"# Operating contract\n{build_loop_skill()}\n\n"
        f"# Constitution (do not violate)\n{constitution_summary()}\n"
    )
