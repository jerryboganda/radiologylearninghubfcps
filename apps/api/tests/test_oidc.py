from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import jwt
import pytest
from apps.api.app.core.config import Settings
from apps.api.app.security.oidc import (
    OIDCVerificationError,
    OIDCVerifier,
    identity_from_claims,
    resolve_current_membership,
)
from cryptography.hazmat.primitives.asymmetric import rsa


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


def test_oidc_verifier_requires_configured_api_audience(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {
            "iss": "https://id.example/realms/radbrain",
            "aud": "radbrain-api",
            "sub": "10000000-0000-0000-0000-000000000001",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
    )

    class _SigningKey:
        key = private_key.public_key()

    class _JWKClient:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def get_signing_key_from_jwt(self, _token: str) -> _SigningKey:
            return _SigningKey()

    monkeypatch.setattr(jwt, "PyJWKClient", _JWKClient)
    verifier = OIDCVerifier(
        Settings(
            oidc_issuer="https://id.example/realms/radbrain",
            oidc_client_id="radbrain-api",
        )
    )

    assert verifier.verify(token).subject == UUID("10000000-0000-0000-0000-000000000001")

    wrong_audience_token = jwt.encode(
        {
            "iss": "https://id.example/realms/radbrain",
            "aud": "radbrain-web",
            "sub": "10000000-0000-0000-0000-000000000001",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
    )
    with pytest.raises(OIDCVerificationError, match="invalid access token"):
        verifier.verify(wrong_audience_token)


def test_oidc_identity_rejects_invalid_subject() -> None:
    try:
        identity_from_claims({"sub": "not-a-uuid"})
    except OIDCVerificationError as exc:
        assert "invalid subject" in str(exc)
    else:
        raise AssertionError("invalid subject was accepted")
