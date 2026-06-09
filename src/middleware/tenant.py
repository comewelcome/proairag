import uuid
from typing import Annotated, Any
from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.models.user import User
from src.db.session import async_session


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        public_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in public_paths:
            return await call_next(request)

        # Try JWT auth first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            user_context = await self._resolve_jwt(token)
            if user_context:
                request.state.tenant_id = user_context["tenant_id"]
                request.state.tenant = user_context["tenant"]
                request.state.user_id = user_context["user_id"]
                request.state.user = user_context["user"]
                request.state.is_tenant_admin = user_context["is_tenant_admin"]
                request.state.auth_mode = "jwt"
                response = await call_next(request)
                return response

        # Fall back to API key auth
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="Missing authentication. Provide Authorization: Bearer *** or X-API-Key header",
            )

        async with async_session() as session:
            result = await session.execute(
                select(Tenant).where(
                    Tenant.api_key == api_key, Tenant.is_active == True
                )
            )
            tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

        request.state.tenant_id = tenant.id
        request.state.tenant = tenant
        request.state.auth_mode = "api_key"

        response = await call_next(request)
        return response

    async def _resolve_jwt(self, token: str) -> dict[str, Any] | None:
        from src.services.auth_service import AuthService

        payload = AuthService.decode_token(token)
        if not payload:
            return None

        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])

        async with async_session() as session:
            result = await session.execute(
                select(User).where(
                    User.id == user_id,
                    User.tenant_id == tenant_id,
                    User.is_active == True,
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                return None

            tenant_result = await session.execute(
                select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active == True)
            )
            tenant = tenant_result.scalar_one_or_none()
            if not tenant:
                return None

        return {
            "user_id": user.id,
            "user": user,
            "tenant_id": tenant.id,
            "tenant": tenant,
            "is_tenant_admin": payload.get("is_tenant_admin", False),
        }


def get_tenant_id(request: Request) -> uuid.UUID:
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(status_code=400, detail="Tenant context missing")
    return request.state.tenant_id


def get_tenant(request: Request) -> Tenant:
    if not hasattr(request.state, "tenant"):
        raise HTTPException(status_code=400, detail="Tenant context missing")
    return request.state.tenant


def get_user_id(request: Request) -> uuid.UUID | None:
    return getattr(request.state, "user_id", None)


def get_user(request: Request) -> User | None:
    return getattr(request.state, "user", None)


def get_is_tenant_admin(request: Request) -> bool:
    return getattr(request.state, "is_tenant_admin", False)


def get_auth_mode(request: Request) -> str:
    return getattr(request.state, "auth_mode", "api_key")


TenantId = Annotated[uuid.UUID, Depends(get_tenant_id)]
TenantDep = Annotated[Tenant, Depends(get_tenant)]
UserId = Annotated[uuid.UUID | None, Depends(get_user_id)]
UserDep = Annotated[User | None, Depends(get_user)]
IsTenantAdmin = Annotated[bool, Depends(get_is_tenant_admin)]
AuthMode = Annotated[str, Depends(get_auth_mode)]
