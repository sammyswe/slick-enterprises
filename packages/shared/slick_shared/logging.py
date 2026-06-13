"""Minimal structured logging setup shared across services."""

from __future__ import annotations

import logging
import sys

from .config import get_settings

_configured = False


def setup_logging(service_name: str = "slick") -> logging.Logger:
    """Configure root logging once and return a named logger."""
    global _configured
    if not _configured:
        settings = get_settings()
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            stream=sys.stdout,
        )
        _configured = True
    return logging.getLogger(service_name)
