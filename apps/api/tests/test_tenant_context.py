from __future__ import annotations

from uuid import UUID

from apps.api.app.db.session import (
    current_tenant_id,
    reset_tenant_context,
    set_tenant_context,
    tenant_context,
)


def test_tenant_context_is_scoped_and_restored() -> None:
    tenant_id = UUID("20000000-0000-0000-0000-000000000002")
    assert current_tenant_id() is None
    with tenant_context(tenant_id):
        assert current_tenant_id() == tenant_id
    assert current_tenant_id() is None


def test_nested_tenant_context_restores_parent() -> None:
    parent = UUID("20000000-0000-0000-0000-000000000002")
    child = UUID("30000000-0000-0000-0000-000000000003")
    token = set_tenant_context(parent)
    try:
        with tenant_context(child):
            assert current_tenant_id() == child
        assert current_tenant_id() == parent
    finally:
        reset_tenant_context(token)
    assert current_tenant_id() is None
