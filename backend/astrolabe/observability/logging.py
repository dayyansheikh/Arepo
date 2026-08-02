"""Structured logging setup.

Human-readable in development; single-line JSON in production (``LOG_JSON=true``) so logs are
grep-able and shippable. No secrets are ever logged (we hold none), and error responses to
clients never include stack traces (see api error handling).
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Minimal structured JSON formatter."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Attach structured extras placed on the record via ``extra={...}``.
        for key, value in getattr(record, "__dict__", {}).items():
            if key.startswith("ctx_"):
                payload[key[4:]] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Configure the root logger once (idempotent)."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    # Clear pre-existing handlers so re-config in tests/reload is clean.
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s")
        )
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
