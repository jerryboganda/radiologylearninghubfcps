"""Typed evaluation fixture contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from uuid import UUID

from packages.models.routing import RouteName
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class EvalCase(BaseModel):
    """One synthetic contract case linked to a versioned prompt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    prompt: str = Field(pattern=r"^[a-z][a-z0-9_]*/v[1-9][0-9]*\.yaml$")
    route: RouteName
    tenant_id: UUID
    input: dict[str, JsonValue]
    expected: dict[str, JsonValue]
    assertions: tuple[str, ...] = Field(min_length=1)


class EvalFixtureSet(BaseModel):
    """Schema for synthetic, source-free evaluation placeholders."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    fixture_set_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    status: Literal["placeholder", "review_required", "approved"]
    data_class: Literal["synthetic"]
    cases: tuple[EvalCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_cases(self) -> EvalFixtureSet:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("eval case IDs must be unique")
        return self


def load_eval_fixtures(path: Path) -> EvalFixtureSet:
    """Load a typed JSON eval fixture set."""

    return EvalFixtureSet.model_validate_json(path.read_text(encoding="utf-8"))
