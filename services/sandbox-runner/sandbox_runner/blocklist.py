"""Dangerous-command detection.

These patterns are blocked unless an explicit approval token accompanies the request.
Blocked actions are always audit-logged. See docs/11-security-model.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Each rule: (name, compiled regex, human explanation).
_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("rm_rf", re.compile(r"\brm\s+(-[a-zA-Z]*\s+)*-[a-zA-Z]*r[a-zA-Z]*f", re.I), "recursive force delete"),
    ("rm_rf2", re.compile(r"\brm\s+-rf\b", re.I), "recursive force delete"),
    ("sudo", re.compile(r"\bsudo\b", re.I), "privilege escalation"),
    ("chmod_outside", re.compile(r"\bchmod\b", re.I), "permission change (verify scope)"),
    ("chown_outside", re.compile(r"\bchown\b", re.I), "ownership change (verify scope)"),
    ("read_ssh", re.compile(r"~/\.ssh|/\.ssh/|id_rsa|id_ed25519", re.I), "reading SSH keys"),
    ("read_env", re.compile(r"(^|\s)(cat|less|more|head|tail|nano|vim)\s+[^\n]*\.env(\s|$)", re.I), "reading .env directly"),
    ("curl_pipe_sh", re.compile(r"(curl|wget)\s+[^\n|]*\|\s*(sudo\s+)?(ba)?sh", re.I), "remote code execution (curl|bash)"),
    ("docker_privileged", re.compile(r"docker\s+run[^\n]*--privileged", re.I), "privileged docker container"),
    ("git_force_push", re.compile(r"git\s+push[^\n]*(--force|-f)\b", re.I), "force push"),
]


@dataclass
class BlockDecision:
    blocked: bool
    rule: str = ""
    reason: str = ""


def check_command(command: str) -> BlockDecision:
    """Return a BlockDecision for a command string."""
    for name, pattern, reason in _RULES:
        if pattern.search(command):
            return BlockDecision(blocked=True, rule=name, reason=reason)
    return BlockDecision(blocked=False)
