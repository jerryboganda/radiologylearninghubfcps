from types import SimpleNamespace
from uuid import UUID

import pytest
from apps.api.app.security.oidc import (
    OIDCVerificationError,
    identity_from_claims,
    resolve_current_membership,
)


class _MembershipSession:
    def __init__(self, rows: list[tuple[UUID, str]]) -> None:
        self._rows = rows

    async def execute(self, statement, parameters):  # type: ignore[no-untyped-def]
        assert parameters["subject"] == "10000000-0000-0000-0000-000000000001"
        return SimpleNamespace(all=lambda: self._rows)


@pytest.mark.asyncio
async def test_current_database_membership_supplies_tenant_and_role() -> None:
    subject = UUID("10000000-0000-0000-0000-000000000001")
    tenant_id = UUID("20000000-0000-0000-0000-000000000002")
    principal = await resolve_current_membership(
        _MembershipSession([(tenant_id, "org_admin")]), subject
    )
    assert principal.user_id == subject
    assert principal.tenant_id == tenant_id
    assert principal.role == "org_admin"


@pytest.mark.asyncio
async def test_ambiguous_current_membership_is_rejected() -> None:
    subject = UUID("10000000-0000-0000-0000-000000000001")
    with pytest.raises(OIDCVerificationError, match="exactly one"):
        await resolve_current_membership(
            _MembershipSession(
                [
                    (UUID("20000000-0000-0000-0000-000000000002"), "student"),
                    (UUID("30000000-0000-0000-0000-000000000003"), "student"),
                ]
            ),
            subject,
        )


def test_oidc_identity_ignores_tenant_and_role_claims() -> None:
    identity = identity_from_claims(
        {
            "sub": "10000000-0000-0000-0000-000000000001",
            "memberships": [
                {
                    "tenant_id": "20000000-0000-0000-0000-000000000002",
                    "role": "superadmin",
                    "active": False,
                }
            ],
        }
    )
    assert identity.subject == UUID("10000000-0000-0000-0000-000000000001")


def test_oidc_identity_rejects_invalid_subject() -> None:
    try:
        identity_from_claims({"sub": "not-a-uuid"})
    except OIDCVerificationError as exc:
        assert "invalid subject" in str(exc)
    else:
        raise AssertionError("invalid subject was accepted")
