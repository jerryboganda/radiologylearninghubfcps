from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from apps.worker.app.job_id import IngestStep, JobId
from evals.contracts import load_eval_fixtures
from packages.curriculum.contracts import load_curriculum_pack
from packages.models.routing import RouteName, load_model_routing_config
from packages.prompts.contracts import load_prompt

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = (
    ROOT / "apps" / "api" / "migrations" / "versions" / "20260924_0001_m0_foundation.py",
    ROOT / "apps" / "api" / "migrations" / "versions" / "20260924_0002_m0_rls.py",
)
MODEL_CONFIG = ROOT / "packages" / "models" / "models.yaml"
CURRICULUM = ROOT / "packages" / "curriculum" / "fcps2_radiology.json"
EVAL_FIXTURE = ROOT / "evals" / "fixtures" / "synthetic_smoke_v1.json"
PROMPT_ROOT = ROOT / "packages" / "prompts"


def test_migration_defines_rls_and_role_separation() -> None:
    sql = "\n".join(path.read_text(encoding="utf-8") for path in MIGRATIONS)
    tenant_tables = (
        "tenants",
        "users",
        "memberships",
        "sources",
        "jobs",
        "job_steps",
        "audit_log",
    )
    for table in tenant_tables:
        assert f"CREATE TABLE {table}" in sql
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE FUNCTION app.current_tenant_id()" in sql
    assert "current_setting('app.tenant_id', true)" in sql
    assert "_MIGRATOR_ROLE = \"radbrain_migrator\"" in sql
    assert "_RUNTIME_ROLE = \"radbrain_app\"" in sql
    assert "rolbypassrls" in sql
    assert "REVOKE ALL ON app.resolve_memberships(text) FROM PUBLIC" in sql
    assert "GRANT EXECUTE ON FUNCTION app.resolve_memberships(text)" in sql
    assert "rights_status IN ('authored', 'licensed')" in sql
    assert "deleted_at IS NULL" in sql
    assert "jobs(tenant_id, id, entity_id, pipeline_version)" in sql
    assert "GRANT UPDATE, DELETE ON audit_log" not in sql


def test_model_routes_are_stable_and_mock_only() -> None:
    config = load_model_routing_config(MODEL_CONFIG)

    assert set(config.routes) == set(RouteName)
    assert config.default_backend == "mock"
    assert config.provider_gate.status == "blocked"
    assert config.provider_gate.external_egress_allowed is False
    assert config.allow_ungrounded_default is False
    for route in config.routes.values():
        assert route.fallbacks == ()
        assert route.targets
        for target in route.targets:
            assert target.backend == "mock"
            assert target.model == "mock-only"
            assert target.api_key_env is None
            assert target.base_url is None


@pytest.mark.parametrize("route", list(RouteName))
def test_every_route_has_a_versioned_prompt(route: RouteName) -> None:
    prompt_path = PROMPT_ROOT / route.value / "v1.yaml"
    prompt = load_prompt(prompt_path)

    assert prompt.agent == route.value
    assert prompt.route == route
    assert prompt.status == "placeholder"
    assert prompt.safety.allow_ungrounded is False
    assert prompt.safety.source_text_is_data is True
    assert prompt.fixture == "evals/fixtures/synthetic_smoke_v1.json"


def test_placeholder_prompts_are_valid_and_reference_fixture() -> None:
    prompt_paths = sorted(PROMPT_ROOT.glob("*/v*.yaml"))

    assert prompt_paths
    for path in prompt_paths:
        prompt = load_prompt(path)
        assert path.parent.name == prompt.agent
        assert path.name == f"v{prompt.version}.yaml"
        assert (ROOT / "packages" / "prompts" / prompt.output_schema).is_file()


def test_curriculum_is_an_explicit_unvalidated_placeholder() -> None:
    pack = load_curriculum_pack(CURRICULUM)

    assert pack.status == "placeholder_unvalidated"
    assert pack.exam_blueprint is None
    assert len(pack.nodes) == 17
    assert all(node.exam_weight is None for node in pack.nodes)


def test_eval_fixture_is_synthetic_and_links_existing_prompts() -> None:
    fixture = load_eval_fixtures(EVAL_FIXTURE)

    assert fixture.schema_version == 1
    assert fixture.status == "placeholder"
    assert fixture.data_class == "synthetic"
    assert fixture.cases
    for case in fixture.cases:
        prompt_path = ROOT / "packages" / "prompts" / case.prompt
        assert prompt_path.is_file()
        assert case.tenant_id


def test_job_id_is_stable_and_includes_pipeline_version() -> None:
    tenant_id = UUID("20000000-0000-0000-0000-000000000002")
    entity_id = UUID("40000000-0000-0000-0000-000000000004")
    job_id = JobId.from_parts(tenant_id, entity_id, IngestStep.KNOWLEDGE_EXTRACTION, 7)

    assert job_id.tenant_id == tenant_id
    assert job_id.entity_id == entity_id
    assert job_id.step is IngestStep.KNOWLEDGE_EXTRACTION
    assert job_id.pipeline_version == 7
    assert str(job_id) == (
        "20000000-0000-0000-0000-000000000002:"
        "40000000-0000-0000-0000-000000000004:"
        "knowledge_extraction:v7"
    )
    assert JobId.from_key(str(job_id)) == job_id
