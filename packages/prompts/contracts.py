"""Typed contracts for versioned prompt files."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from packages.models.routing import RouteName


class PromptSafety(BaseModel):
    """Prompt invariants that are not safe to override per deployment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allow_ungrounded: Literal[False] = False
    source_text_is_data: Literal[True] = True
    provenance_required: Literal[True] = True
    reject_tools: Literal[True] = True
    reject_source_originated_links: Literal[True] = True


class PromptFile(BaseModel):
    """Strict schema for ``packages/prompts/<agent>/vN.yaml``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    agent: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    version: int = Field(ge=1)
    route: RouteName
    status: Literal["placeholder", "active", "retired"]
    description: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    input_variables: tuple[str, ...] = ()
    output_schema: str = Field(pattern=r"^schemas/.+\.json$")
    fixture: str = Field(pattern=r"^evals/fixtures/.+\.json$")
    safety: PromptSafety

    @model_validator(mode="after")
    def require_route_agent_match(self) -> PromptFile:
        if self.route.value != self.agent:
            raise ValueError("prompt agent must match its stable model route")
        return self


def load_prompt(path: Path) -> PromptFile:
    """Load a versioned prompt fixture."""

    with path.open(encoding="utf-8") as prompt_file:
        payload = yaml.safe_load(prompt_file)
    return PromptFile.model_validate(payload)
