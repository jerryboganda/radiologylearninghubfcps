from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, Request, status


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: UUID
    tenant_id: UUID
    role: str = "student"


def require_tenant(request: Request) -> UUID:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not isinstance(tenant_id, UUID):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="tenant context required",
        )
    return tenant_id


def require_roles(principal: Principal, *allowed_roles: str) -> Principal:
    if principal.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    return principal
