from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, Any, cast
from uuid import UUID

from apps.api.app.core.config import get_settings
from apps.api.app.db.session import (
    get_system_session,
    reset_tenant_context,
    set_tenant_context,
)
from apps.api.app.schemas.common import (
    ErrorResponse,
    ExportJobResponse,
    HealthResponse,
    TenantResponse,
)
from apps.api.app.security.oidc import (
    OIDCVerificationError,
    OIDCVerifier,
    resolve_current_membership,
)
from apps.api.app.security.principal import Principal, require_roles
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

app = FastAPI(
    title="radbrain API",
    version="0.1.0",
    description="Provenance-first, tenant-isolated radiology study platform.",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)
oidc_verifier = OIDCVerifier(settings)


@app.middleware("http")
async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request.state.request_id = request.headers.get("x-request-id")
    return await call_next(request)


@app.get("/health/live", response_model=HealthResponse, tags=["health"])
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok", service="api", environment=settings.app_env)


@app.get("/health/ready", response_model=HealthResponse, tags=["health"])
async def readiness(
    session: Annotated[AsyncSession, Depends(get_system_session)],
) -> HealthResponse:
    try:
        import redis.asyncio as redis

        await session.execute(text("SELECT 1"))
        redis_client = cast(Any, redis).from_url(settings.redis_url, socket_connect_timeout=1)
        try:
            await redis_client.ping()
        finally:
            await redis_client.aclose()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="dependency unavailable") from exc
    return HealthResponse(status="ready", service="api", environment=settings.app_env)


def _local_principal(
    x_user_id: str | None,
    x_tenant_id: str | None,
    x_role: str | None,
) -> Principal | None:
    if not x_user_id or not x_tenant_id:
        return None
    try:
        user_id = UUID(x_user_id)
        tenant_id = UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid local identity") from exc
    allowed_roles = {"student", "editor", "org_admin", "superadmin"}
    role = x_role or "student"
    if role not in allowed_roles:
        raise HTTPException(status_code=400, detail="invalid local role")
    return Principal(user_id=user_id, tenant_id=tenant_id, role=role)


async def principal_from_request(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    request: Request,
    session: Annotated[AsyncSession, Depends(get_system_session)],
    x_user_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
) -> Principal:
    """Authenticate OIDC access and resolve current membership from the database."""
    if credentials is not None:
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="bearer token required")
        try:
            identity = oidc_verifier.verify(credentials.credentials)
            principal = await resolve_current_membership(session, identity.subject)
        except OIDCVerificationError as exc:
            raise HTTPException(status_code=401, detail="invalid access token") from exc
        request.state.tenant_id = principal.tenant_id
        return principal

    if not settings.is_local_development:
        raise HTTPException(status_code=401, detail="OIDC token required")

    local_principal = _local_principal(x_user_id, x_tenant_id, x_role)
    if local_principal is None:
        raise HTTPException(status_code=401, detail="authentication required")
    request.state.tenant_id = local_principal.tenant_id
    return local_principal


async def principal_context(
    principal: Annotated[Principal, Depends(principal_from_request)],
) -> AsyncIterator[Principal]:
    token = set_tenant_context(principal.tenant_id)
    try:
        yield principal
    finally:
        reset_tenant_context(token)


@app.get(f"{settings.api_prefix}/me", response_model=TenantResponse, tags=["auth"])
async def me(principal: Annotated[Principal, Depends(principal_context)]) -> TenantResponse:
    return TenantResponse(
        id=str(principal.tenant_id),
        name="Authenticated tenant",
        kind="solo",
        role=principal.role,
    )


@app.post(f"{settings.api_prefix}/tenants/switch", response_model=TenantResponse, tags=["auth"])
async def switch_tenant(
    tenant_id: UUID,
    principal: Annotated[Principal, Depends(principal_context)],
) -> TenantResponse:
    if tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="tenant switch denied")
    return TenantResponse(
        id=str(tenant_id),
        name="Authenticated tenant",
        kind="solo",
        role=principal.role,
    )


@app.post(
    f"{settings.api_prefix}/me/export",
    response_model=ExportJobResponse,
    status_code=202,
    tags=["data-rights"],
)
async def export_data(
    principal: Annotated[Principal, Depends(principal_context)],
) -> ExportJobResponse:
    return ExportJobResponse(job_id=f"export:{principal.user_id}", status="queued")


@app.delete(f"{settings.api_prefix}/me", status_code=202, tags=["data-rights"])
async def delete_account(
    principal: Annotated[Principal, Depends(principal_context)],
) -> dict[str, str]:
    return {"status": "queued", "job_id": f"delete:{principal.user_id}"}


@app.get(f"{settings.api_prefix}/admin/ping", tags=["admin"])
async def admin_ping(
    principal: Annotated[Principal, Depends(principal_context)],
) -> dict[str, str]:
    require_roles(principal, "org_admin", "superadmin")
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.api.app.main:app", host="127.0.0.1", port=8000, reload=settings.debug)
