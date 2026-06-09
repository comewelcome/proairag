import uuid
import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: TenantCreate) -> Tenant:
        api_key = data.api_key or f"sk-{secrets.token_urlsafe(32)}"
        tenant = Tenant(name=data.name, api_key=api_key)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_api_key(self, api_key: str) -> Tenant | None:
        result = await self.db.execute(
            select(Tenant).where(Tenant.api_key == api_key)
        )
        return result.scalar_one_or_none()

    async def update(self, tenant_id: uuid.UUID, data: TenantUpdate) -> Tenant | None:
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tenant, key, value)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def deactivate(self, tenant_id: uuid.UUID) -> bool:
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False
        tenant.is_active = False
        await self.db.commit()
        return True


def get_tenant_service(db: AsyncSession) -> TenantService:
    return TenantService(db)
