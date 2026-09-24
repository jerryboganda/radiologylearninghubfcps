"""Minimal structured observability for the M0 API boundary."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class RedactingJsonFormatter(logging.Formatter):
    """Emit only allowlisted operational fields as one JSON object."""

    _events = frozenset({"request_completed"})
    _fields = ("request_id", "method", "path", "status_code")

    def format(self, record: logging.LogRecord) -> str:
        event = record.getMessage() if record.getMessage() in self._events else "unknown_event"
        payload: dict[str, Any] = {
            "event": event,
            "service": "api",
        }
        for field in self._fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging() -> logging.Logger:
    """Configure the API's bounded, non-content-bearing log format."""

    logger = logging.getLogger("radbrain.api")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(RedactingJsonFormatter())
        logger.addHandler(handler)
    return logger


logger = configure_logging()
