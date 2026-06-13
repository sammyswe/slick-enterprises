"""Make service/app packages importable in tests without installing each one."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for rel in ("apps/gateway", "services/sandbox-runner", "services/orchestrator"):
    sys.path.insert(0, str(ROOT / rel))

# Force mock mode + a harmless DB URL for any import-time settings access.
os.environ.setdefault("MODEL_MOCK_MODE", "true")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
