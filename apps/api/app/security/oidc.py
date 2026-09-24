from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from apps.api.app.core.config import Settings
from apps.api.app.security.principal import Principal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_ALLOWED_ROLES = frozenset({"student", "editor", "org_admin", "superadmin"})


@dataclass(frozen=True, slots=True)
class OIDCIdentity:
    subject: UUID


class OIDCVerificationError(ValueError):
    """Raised when an access token does not establish a valid identity."""


class OIDCVerifier:
    """Verify Keycloak-compatible OIDC access tokens without request-time network setup."""

    def __init__(self, settings: Settings) -> None:
        self._issuer = settings.oidc_issuer.rstrip("/")
        self._audience = settings.oidc_audience
        self._jwks_url = settings.oidc_jwks_url or (
            f"{self._issuer}/protocol/openid-connect/certs"
        )
        self._client: Any | None = None

    def verify(self, token: str) -> OIDCIdentity:
        try:
            import jwt
        except ImportError as exc:  # pragma: no cover - packaged installations provide PyJWT
            raise OIDCVerificationError("OIDC verifier is not installed") from exc

        try:
            if self._client is None:
                self._client = jwt.PyJWKClient(self._jwks_url, cache_keys=True)
            signing_key = self._client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self._audience,
                issuer=self._issuer,
                leeway=30,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except Exception as exc:  # JWT/JWKS errors must not become 500s.
            raise OIDCVerificationError("invalid access token") from exc

        return identity_from_claims(claims)


def identity_from_claims(claims: Mapping[str, Any]) -> OIDCIdentity:
    """Validate the token subject without trusting tenant or role claims."""

    subject = claims.get("sub")
    if not isinstance(subject, str):
        raise OIDCVerificationError("missing subject")
    try:
        return OIDCIdentity(subject=UUID(subject))
    except ValueError as exc:
        raise OIDCVerificationError("invalid subject") from exc


async def resolve_current_membership(
    session: AsyncSession, subject: UUID
) -> Principal:
    """Resolve exactly one current active membership from the authoritative database."""

    result = await session.execute(
        text("SELECT tenant_id, role FROM app.resolve_memberships(:subject)"),
        {"subject": str(subject)},
    )
    rows = result.all()
    if len(rows) != 1:
        raise OIDCVerificationError("exactly one active membership required")
    tenant_value, role = rows[0]
    if not isinstance(role, str) or role not in _ALLOWED_ROLES:
        raise OIDCVerificationError("invalid current membership role")
    try:
        tenant_id = UUID(str(tenant_value))
    except ValueError as exc:
        raise OIDCVerificationError("invalid current membership tenant") from exc
    return Principal(user_id=subject, tenant_id=tenant_id, role=role)
