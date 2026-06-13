"""Sandbox runner API.

Executes commands inside a constrained working directory, blocking dangerous commands
unless an explicit approval token is supplied. Every request is audit-logged.
"""

from __future__ import annotations

import shlex
import subprocess
import time

from fastapi import FastAPI
from pydantic import BaseModel

from slick_shared.config import get_settings
from slick_shared.logging import setup_logging

from .blocklist import check_command

logger = setup_logging("sandbox-runner")
settings = get_settings()

app = FastAPI(title="Slick Sandbox Runner", version="0.1.0")

# In-memory audit log (v1). Phase 1: persist to DB / signed log.
AUDIT: list[dict] = []
WORKDIR = "/workspace"


class CommandRequest(BaseModel):
    command: str
    cwd: str = WORKDIR
    approval_token: str | None = None  # required to run a blocked command
    timeout: int = 60
    agent: str = ""
    task_id: str | None = None


class CommandResult(BaseModel):
    allowed: bool
    blocked_reason: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


def _audit(entry: dict) -> None:
    entry["ts"] = time.time()
    AUDIT.append(entry)
    logger.info("AUDIT %s", entry)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "slick-sandbox-runner", "audit_entries": len(AUDIT)}


@app.get("/audit")
async def audit(limit: int = 100) -> list[dict]:
    return AUDIT[-limit:]


@app.post("/exec", response_model=CommandResult)
async def exec_command(req: CommandRequest) -> CommandResult:
    decision = check_command(req.command)

    if decision.blocked and (settings.sandbox_require_approval_for_dangerous and not req.approval_token):
        _audit(
            {
                "event": "blocked",
                "command": req.command,
                "rule": decision.rule,
                "reason": decision.reason,
                "agent": req.agent,
                "task_id": req.task_id,
            }
        )
        return CommandResult(allowed=False, blocked_reason=f"{decision.rule}: {decision.reason}")

    _audit(
        {
            "event": "exec",
            "command": req.command,
            "approved_override": bool(decision.blocked and req.approval_token),
            "agent": req.agent,
            "task_id": req.task_id,
        }
    )

    try:
        proc = subprocess.run(
            shlex.split(req.command),
            cwd=req.cwd,
            capture_output=True,
            text=True,
            timeout=req.timeout,
            check=False,
        )
        return CommandResult(
            allowed=True,
            exit_code=proc.returncode,
            stdout=proc.stdout[-10000:],
            stderr=proc.stderr[-10000:],
        )
    except subprocess.TimeoutExpired:
        return CommandResult(allowed=True, exit_code=124, stderr="command timed out")
    except FileNotFoundError as exc:
        return CommandResult(allowed=True, exit_code=127, stderr=str(exc))
