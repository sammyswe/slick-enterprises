"""MCP adapter registry — resolves agent plan MCP names to runnable stdio commands."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import get_settings

_MOCK_ADAPTER = Path(__file__).resolve().parents[3] / "services" / "mcp-adapters" / "mock_mcp.py"


def _mock_stdio_config(name: str) -> dict[str, Any]:
    """Generic mock MCP that logs tool calls to artifacts."""
    python = os.environ.get("PYTHON", "python3")
    adapter = _MOCK_ADAPTER
    if not adapter.is_file():
        # Inside container: /workspace/services/mcp-adapters/mock_mcp.py
        adapter = Path(get_settings().slick_repo_root) / "services" / "mcp-adapters" / "mock_mcp.py"
    return {
        "name": name,
        "command": python,
        "args": [str(adapter), "--server-name", name],
    }


def resolve_mcp_entry(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a plan MCP declaration into a Cursor SDK-ready config."""
    name = str(raw.get("name") or "").strip()
    if not name:
        return None

    # Explicit command/url from the plan wins.
    if raw.get("url"):
        entry: dict[str, Any] = {"name": name, "url": raw["url"]}
        if raw.get("headers"):
            entry["headers"] = raw["headers"]
        return entry
    if raw.get("command"):
        entry = {"name": name, "command": raw["command"]}
        if raw.get("args"):
            entry["args"] = list(raw["args"])
        if raw.get("env"):
            entry["env"] = dict(raw["env"])
        return entry

    # Registry lookup: named adapters can be added here later.
    registry: dict[str, dict[str, Any]] = {}
    if name in registry:
        return dict(registry[name])

    # Default: mock stdio adapter for headless testing.
    return _mock_stdio_config(name)


def resolve_mcp_servers_for_agent(mcp_servers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve all MCP servers declared on an agent."""
    resolved: list[dict[str, Any]] = []
    for raw in mcp_servers or []:
        if not isinstance(raw, dict):
            continue
        entry = resolve_mcp_entry(raw)
        if entry:
            resolved.append(entry)
    return resolved
