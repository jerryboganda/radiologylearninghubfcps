from __future__ import annotations

import logging

from apps.api.app.observability import RedactingJsonFormatter


def test_formatter_keeps_only_allowlisted_operational_fields() -> None:
    record = logging.LogRecord(
        name="radbrain.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "10000000-0000-0000-0000-000000000001"
    record.method = "GET"
    record.path = "/health/live"
    record.status_code = 200
    record.source_text = "synthetic private text must not be emitted"
    record.authorization = "Bearer must-not-be-emitted"
    record.msg = "source text must not become an event"

    payload = RedactingJsonFormatter().format(record)

    assert '"source text must not become an event"' not in payload
    assert '"event":"unknown_event"' in payload
    assert '"source_text"' not in payload
    assert '"authorization"' not in payload
    assert '"request_id":"10000000-0000-0000-0000-000000000001"' in payload
    assert '"status_code":200' in payload
