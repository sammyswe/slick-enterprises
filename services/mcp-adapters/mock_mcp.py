#!/usr/bin/env python3
"""Generic mock MCP server (stdio). Logs tool calls; writes artifact JSON for tests."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-name", default="mock-mcp")
    args = parser.parse_args()
    server_name = args.server_name

    _send(
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
    )

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        req_id = msg.get("id")
        method = msg.get("method", "")

        if method == "initialize":
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": server_name, "version": "0.1.0"},
                    },
                }
            )
        elif method == "tools/list":
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "mock_action",
                                "description": f"Mock tool for {server_name}",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"payload": {"type": "string"}},
                                },
                            }
                        ]
                    },
                }
            )
        elif method == "tools/call":
            params = msg.get("params") or {}
            tool_name = params.get("name", "mock_action")
            tool_args = params.get("arguments") or {}
            artifact = {
                "server": server_name,
                "tool": tool_name,
                "arguments": tool_args,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "mock_ok",
            }
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(artifact, indent=2),
                            }
                        ]
                    },
                }
            )
        elif method == "ping":
            _send({"jsonrpc": "2.0", "id": req_id, "result": {}})


if __name__ == "__main__":
    main()
