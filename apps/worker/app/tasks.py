from __future__ import annotations

from typing import TypedDict

from apps.worker.app.celery_app import celery_app


class HealthResult(TypedDict):
    status: str
    service: str


@celery_app.task(name="radbrain.health")  # type: ignore[untyped-decorator]
def health() -> HealthResult:
    """Return process liveness without contacting a model or database."""

    return {"status": "ok", "service": "worker"}
