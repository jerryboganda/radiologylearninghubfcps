"""Stable job identity for idempotent, resumable worker steps."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

_JOB_KEY = re.compile(
    r"^(?P<tenant>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}):"
    r"(?P<entity>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}):"
    r"(?P<step>[a-z][a-z0-9_]*):v(?P<version>[1-9][0-9]*)$"
)


class IngestStep(StrEnum):
    """Canonical nine-step ingestion vocabulary."""

    UPLOAD_DEDUPE_SCAN = "upload_dedupe_scan"
    RENDER_PAGES = "render_pages"
    PARSE_LAYOUT = "parse_layout"
    EXTRACT_FIGURES = "extract_figures"
    EXTRACT_TABLES = "extract_tables"
    CHUNK = "chunk"
    EMBED_INDEX = "embed_index"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    READY_NOTIFY = "ready_notify"


@dataclass(frozen=True, slots=True)
class JobId:
    """Idempotency identity scoped by tenant, entity, step, and pipeline version."""

    tenant_id: UUID
    entity_id: UUID
    step: IngestStep
    pipeline_version: int

    def __post_init__(self) -> None:
        if self.pipeline_version < 1:
            raise ValueError("pipeline_version must be positive")

    @classmethod
    def from_parts(
        cls,
        tenant_id: UUID,
        entity_id: UUID,
        step: IngestStep,
        pipeline_version: int,
    ) -> JobId:
        return cls(tenant_id, entity_id, step, pipeline_version)

    @classmethod
    def from_key(cls, key: str) -> JobId:
        """Parse a canonical job key without accepting unversioned identities."""

        match = _JOB_KEY.fullmatch(key)
        if match is None:
            raise ValueError("invalid versioned job id")
        try:
            step = IngestStep(match.group("step"))
        except ValueError as exc:
            raise ValueError("unknown ingestion step") from exc
        return cls(
            tenant_id=UUID(match.group("tenant")),
            entity_id=UUID(match.group("entity")),
            step=step,
            pipeline_version=int(match.group("version")),
        )

    def __str__(self) -> str:
        return (
            f"{self.tenant_id}:{self.entity_id}:{self.step.value}:"
            f"v{self.pipeline_version}"
        )
