"""Typed contracts for the unvalidated curriculum placeholder."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CurriculumNode(BaseModel):
    """One editable ontology node; weights remain unassigned by default."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(pattern=r"^[A-Z0-9][A-Z0-9:._-]*$")
    parent_code: str | None = None
    level: Literal["section", "system", "topic", "subtopic"]
    title: str = Field(min_length=1)
    exam_weight: float | None = Field(default=None, ge=0, le=1)


class CurriculumPack(BaseModel):
    """Schema for a future editor-approved curriculum release."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    status: Literal["placeholder_unvalidated", "editor_validated"]
    source: str = Field(min_length=1)
    exam_blueprint: str | None = None
    nodes: tuple[CurriculumNode, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_ontology(self) -> CurriculumPack:
        codes = [node.code for node in self.nodes]
        if len(codes) != len(set(codes)):
            raise ValueError("curriculum node codes must be unique")
        known_codes = set(codes)
        for node in self.nodes:
            if node.parent_code is not None and node.parent_code not in known_codes:
                raise ValueError(f"unknown curriculum parent: {node.parent_code}")
        if sum(node.level == "section" for node in self.nodes) != 1:
            raise ValueError("curriculum requires exactly one root section")
        if self.status == "placeholder_unvalidated" and any(
            node.exam_weight is not None for node in self.nodes
        ):
            raise ValueError("placeholder curriculum must not assign exam weights")
        if self.status == "placeholder_unvalidated" and self.exam_blueprint is not None:
            raise ValueError("placeholder curriculum must not assign a blueprint")
        return self


def load_curriculum_pack(path: Path) -> CurriculumPack:
    """Load and validate a curriculum JSON pack."""

    return CurriculumPack.model_validate_json(path.read_text(encoding="utf-8"))
