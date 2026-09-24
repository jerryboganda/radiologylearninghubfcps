from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, Token
from uuid import UUID

from apps.api.app.core.config import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_tenant_id: ContextVar[UUID | None] = ContextVar("radbrain_tenant_id", default=None)

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def current_tenant_id() -> UUID | None:
    return _tenant_id.get()


def set_tenant_context(tenant_id: UUID) -> Token[UUID | None]:
    return _tenant_id.set(tenant_id)


def reset_tenant_context(token: Token[UUID | None]) -> None:
    _tenant_id.reset(token)


@contextmanager
def tenant_context(tenant_id: UUID) -> Iterator[None]:
    token = set_tenant_context(tenant_id)
    try:
        yield
    finally:
        reset_tenant_context(token)


async def set_database_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


async def get_system_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


@asynccontextmanager
async def tenant_session(tenant_id: UUID) -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        token = set_tenant_context(tenant_id)
        try:
            await set_database_tenant(session, tenant_id)
            yield session
        finally:
            reset_tenant_context(token)
