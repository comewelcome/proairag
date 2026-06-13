"""Super admin endpoints — global management of tenants, users, documents."""

import uuid
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import IsSuperAdmin
from src.models.tenant import Tenant
from src.models.user import User
from src.models.document import Document
from src.models.user_department import UserDepartment
from src.services.auth_service import pwd_context
from src.schemas.auth import UserResponse
from src.schemas.tenant import TenantResponse
from src.schemas.document import DocumentResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_super_admin(is_super_admin: IsSuperAdmin):  # type: ignore
    if not is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin required")


# ─── Tenants ────────────────────────────────────────────────────────────────

@router.get("/tenants/", response_model=list[TenantResponse])
async def list_all_tenants(
    db: AsyncSession = Depends(get_db),
    is_super_admin: IsSuperAdmin = ...,  # type: ignore
):
    _require_super_admin(is_super_admin)
    result = await db.execute(select(Tenant))
    return result.scalars().all()


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    is_super_admin: IsSuperAdmin = ...,  # type: ignore
):
    _require_super_admin(is_super_admin)
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    tenant = await db.get(Tenant, tid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.is_active = False
    await db.commit()
    return {"status": "deactivated"}


# ─── Users ──────────────────────────────────────────────────────────────────

@router.get("/tenants/{tenant_id}/users/", response_model=list[UserResponse])
async def list_tenant_users(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    is_super_admin: IsSuperAdmin = ...,  # type: ignore
):
    _require_super_admin(is_super_admin)
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    tenant = await db.get(Tenant, tid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    result = await db.execute(select(User).where(User.tenant_id == tid))
    return result.scalars().all()


class AdminUserCreate(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    full_name: str | None = None
    is_tenant_admin: bool = False


@router.post("/tenants/{tenant_id}/users/", response_model=UserResponse, status_code=201)
async def create_user_in_tenant(
    tenant_id: str,
    data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    is_super_admin: IsSuperAdmin = ...,  # type: ignore
):
    _require_super_admin(is_super_admin)
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    tenant = await db.get(Tenant, tid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        tenant_id=tid,
        email=data.email,
        password_hash=pwd_context.hash(data.password),
        full_name=data.full_name,
        is_tenant_admin=data.is_tenant_admin,
        is_super_admin=False,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/tenants/{tenant_id}/users/{user_id}", response_model=UserResponse)
async def update_user(
    tenant_id: str,
    user_id: str,
    data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    is_super_admin: IsSuperAdmin = ...,  # type: ignore
):
    _require_super_admin(is_super_admin)
    try:
        uid = uuid.UUID(user_id)
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID")
    user = await db.get(User, uid)
    if not user or user.tenant_id != tid:
        raise HTTPException(status_code=404, detail="User not found in tenant")

    user.full_name = data.full_name
    user.is_tenant_admin = data.is_tenant_admin
    if data.password:
        user.password_hash = pwd_context.hash(data.password)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/tenants/{tenant_id}/users/{user_id}")
async def delete_user(
    tenant_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    is_super_admin: IsSuperAdmin = ...,  # type: ignore
):
    _require_super_admin(is_super_admin)
    try:
        uid = uuid.UUID(user_id)
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID")
    user = await db.get(User, uid)
    if not user or user.tenant_id != tid:
        raise HTTPException(status_code=404, detail="User not found in tenant")
    await db.execute(sa_delete(UserDepartment).where(UserDepartment.user_id == uid))
    await db.delete(user)
    await db.commit()
    return {"status": "deleted"}


# ─── Documents (cross-tenant view) ─────────────────────────────────────────

@router.get("/tenants/{tenant_id}/documents/", response_model=list[DocumentResponse])
async def list_tenant_documents(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    is_super_admin: IsSuperAdmin = ...,  # type: ignore
):
    _require_super_admin(is_super_admin)
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    result = await db.execute(
        select(Document).where(Document.tenant_id == tid).order_by(Document.created_at.desc())
    )
    return result.scalars().all()
