"""Opt-in live PostgreSQL proof for the M0 tenant RLS boundary."""

from __future__ import annotations

import asyncio
import hashlib
import os
from typing import Any
from uuid import uuid4

import pytest

asyncpg: Any = pytest.importorskip("asyncpg")

_CORE_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _source_hash(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


async def _assert_tenant_isolation() -> None:
    admin_dsn = os.environ["RADBRAIN_RLS_ADMIN_DATABASE_URL"]
    runtime_dsn = os.environ["RADBRAIN_RLS_RUNTIME_DATABASE_URL"]
    tenant_a = uuid4()
    tenant_b = uuid4()
    user_a = uuid4()
    user_b = uuid4()
    source_a = uuid4()
    source_b = uuid4()
    core_source = uuid4()
    admin = await asyncpg.connect(admin_dsn)
    runtime = await asyncpg.connect(runtime_dsn)
    try:
        role = await runtime.fetchrow(
            "SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
            "FROM pg_roles WHERE rolname = current_user"
        )
        assert role is not None
        assert not any(tuple(role))

        async with admin.transaction():
            await admin.execute(
                "INSERT INTO tenants (id, kind, name) VALUES "
                "($1, 'personal', 'RLS Tenant A'), ($2, 'personal', 'RLS Tenant B')",
                tenant_a,
                tenant_b,
            )
            await admin.execute(
                "INSERT INTO users (id, tenant_id, oidc_subject, email) VALUES "
                "($1, $3, 'synthetic-rls-a', 'a@example.invalid'), "
                "($2, $4, 'synthetic-rls-b', 'b@example.invalid')",
                user_a,
                user_b,
                tenant_a,
                tenant_b,
            )
            await admin.execute(
                "INSERT INTO memberships (tenant_id, user_id, role) VALUES "
                "($1, $2, 'student'), ($3, $4, 'student')",
                tenant_a,
                user_a,
                tenant_b,
                user_b,
            )
            await admin.execute(
                "INSERT INTO sources "
                "(id, tenant_id, uploaded_by, kind, scope, sha256, storage_key, "
                "title, status, rights_status) VALUES "
                "($1, $2, $3, 'note', 'private', $4, $5, 'Tenant A', 'ready', "
                "'unverified'), "
                "($6, $7, $8, 'note', 'private', $9, $10, 'Tenant B', 'ready', "
                "'unverified'), "
                "($11, $12, NULL, 'note', 'core', $13, NULL, 'Reviewed Core', "
                "'ready', 'licensed')",
                source_a,
                tenant_a,
                user_a,
                _source_hash("a"),
                f"tenants/{tenant_a}/synthetic-a",
                source_b,
                tenant_b,
                user_b,
                _source_hash("b"),
                f"tenants/{tenant_b}/synthetic-b",
                core_source,
                _CORE_TENANT_ID,
                _source_hash("core"),
            )

        assert await runtime.fetchval("SELECT count(*) FROM sources") == 0

        async with runtime.transaction():
            await runtime.execute(
                "SELECT set_config('app.tenant_id', $1, true)", str(tenant_a)
            )
            visible = {row["id"] for row in await runtime.fetch("SELECT id FROM sources")}
            assert visible == {source_a, core_source}
            cross_tenant_updates = await runtime.fetchval(
                "WITH updated AS ("
                "UPDATE sources SET title = 'forbidden' WHERE id = $1 RETURNING 1"
                ") SELECT count(*) FROM updated",
                source_b,
            )
            assert cross_tenant_updates == 0
            core_updates = await runtime.fetchval(
                "WITH updated AS ("
                "UPDATE sources SET title = 'forbidden' WHERE id = $1 RETURNING 1"
                ") SELECT count(*) FROM updated",
                core_source,
            )
            assert core_updates == 0
            with pytest.raises(asyncpg.PostgresError) as denied:
                await runtime.execute(
                    "INSERT INTO sources "
                    "(tenant_id, uploaded_by, kind, scope, sha256, storage_key, "
                    "title, status, rights_status) VALUES "
                    "($1, $2, 'note', 'private', $3, $4, 'forbidden', 'ready', "
                    "'unverified')",
                    tenant_b,
                    user_b,
                    _source_hash("forbidden"),
                    f"tenants/{tenant_b}/forbidden",
                )
            assert denied.value.sqlstate == "42501"

        assert await runtime.fetchval("SELECT count(*) FROM sources") == 0

        async with runtime.transaction():
            await runtime.execute(
                "SELECT set_config('app.tenant_id', $1, true)", str(tenant_b)
            )
            visible = {row["id"] for row in await runtime.fetch("SELECT id FROM sources")}
            assert visible == {source_b, core_source}
    finally:
        await runtime.close()
        async with admin.transaction():
            await admin.execute(
                "DELETE FROM sources WHERE id = ANY($1::uuid[])",
                [source_a, source_b, core_source],
            )
            await admin.execute(
                "DELETE FROM memberships WHERE tenant_id = ANY($1::uuid[])",
                [tenant_a, tenant_b],
            )
            await admin.execute(
                "DELETE FROM users WHERE id = ANY($1::uuid[])", [user_a, user_b]
            )
            await admin.execute(
                "DELETE FROM tenants WHERE id = ANY($1::uuid[])", [tenant_a, tenant_b]
            )
        await admin.close()


def test_two_tenant_rls_against_runtime_role() -> None:
    required = {
        "RADBRAIN_RLS_ADMIN_DATABASE_URL",
        "RADBRAIN_RLS_RUNTIME_DATABASE_URL",
    }
    if not required.issubset(os.environ):
        pytest.skip("set disposable admin/runtime PostgreSQL URLs to run live RLS proof")
    asyncio.run(_assert_tenant_isolation())
