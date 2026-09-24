from __future__ import annotations

from datetime import UTC, datetime


def now_utc() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return now_utc().isoformat()
