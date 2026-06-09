import uuid
from typing import Annotated
from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.db.session import async_session


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        public_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in public_paths:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(status_code=401, detail="Missing X-API-Key header")

        async with async_session() as session:
            result = await session.execute(
                select(Tenant).where(Tenant.api_key == api_key, Tenant.is_active == True)
            )
            tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

        request.state.tenant_id = tenant.id
        request.state.tenant = tenant

        response = await call_next(request)
        return response


def get_tenant_id(request: Request) -> uuid.UUID:
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(status_code=400, detail="Tenant context missing")
    return request.state.tenant_id


def get_tenant(request: Request) -> Tenant:
    if not hasattr(request.state, "tenant"):
        raise HTTPException(status_code=400, detail="Tenant context missing")
    return request.state.tenant


TenantId = Annotated[uuid.UUID, Depends(get_tenant_id)]
TenantDep = Annotated[Tenant, Depends(get_tenant)]
