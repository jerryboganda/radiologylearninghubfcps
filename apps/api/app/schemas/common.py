from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    service: str
    environment: str


class TenantResponse(BaseModel):
    id: str
    name: str
    kind: str
    role: str


class ErrorResponse(BaseModel):
    detail: str
    request_id: str | None = Field(default=None)


class Citation(BaseModel):
    source_id: str
    page_no: int = Field(ge=1)
    block_id: str
    bbox: list[float] = Field(min_length=4, max_length=4)
    figure_id: str | None = None


class ExportJobResponse(BaseModel):
    job_id: str
    status: str
