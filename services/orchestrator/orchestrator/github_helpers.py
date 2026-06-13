"""GitHub helpers: branch / commit / PR (placeholder).

v1 wraps local `git` and records intended PRs as `github_events`. Real PR creation via
the GitHub API/PAT is a documented Phase-1 extension point. These helpers must respect
the no-direct-push-to-main rule (see .cursor/rules/04-git-workflow.mdc).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from slick_shared.config import get_settings
from slick_shared.logging import setup_logging

logger = setup_logging("orchestrator.github")


@dataclass
class CommitResult:
    ok: bool
    detail: str


def branch_name(kind: str, scope: str, task: str) -> str:
    """Build a clear branch name: agent/<role>/<task> or business/<slug>/<task>."""
    safe = "-".join(task.lower().split())[:40]
    return f"{kind}/{scope}/{safe}"


def create_branch(name: str, cwd: str = ".") -> CommitResult:
    return _run(["git", "checkout", "-b", name], cwd)


def commit(message: str, cwd: str = ".") -> CommitResult:
    add = _run(["git", "add", "-A"], cwd)
    if not add.ok:
        return add
    return _run(["git", "commit", "-m", message], cwd)


def push(branch: str, cwd: str = ".") -> CommitResult:
    settings = get_settings()
    if branch == settings.github_default_branch and not settings.github_allow_direct_push_to_main:
        msg = "Refusing to push directly to main (GITHUB_ALLOW_DIRECT_PUSH_TO_MAIN=false)."
        logger.warning(msg)
        return CommitResult(ok=False, detail=msg)
    return _run(["git", "push", "-u", "origin", branch], cwd)


def open_pr_placeholder(title: str, body: str, branch: str) -> dict:
    """Placeholder: record intended PR. Phase 1 replaces with real GitHub API call."""
    settings = get_settings()
    logger.info("PR (placeholder) title=%r branch=%r", title, branch)
    return {
        "type": "pr",
        "repo": f"{settings.github_owner}/{settings.github_repo}",
        "branch": branch,
        "title": title,
        "body": body,
        "status": "placeholder",
    }


def _run(cmd: list[str], cwd: str) -> CommitResult:
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        ok = out.returncode == 0
        detail = (out.stdout + out.stderr).strip()
        if not ok:
            logger.warning("git command failed: %s -> %s", " ".join(cmd), detail)
        return CommitResult(ok=ok, detail=detail)
    except FileNotFoundError:
        return CommitResult(ok=False, detail="git not available in this environment")
