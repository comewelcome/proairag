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
        await self.db.flush()

        # Create admin user if provided
        if data.admin_email and data.admin_password:
            from src.models.user import User
            from src.services.auth_service import pwd_context
            admin = User(
                tenant_id=tenant.id,
                email=data.admin_email,
                password_hash=pwd_context.hash(data.admin_password),
                full_name=data.admin_full_name,
                is_tenant_admin=True,
            )
            self.db.add(admin)

        # Create default "General" department
        from src.models.department import Department
        general_dept = Department(
            tenant_id=tenant.id,
            name="General",
            description="Default department for all tenant members",
        )
        self.db.add(general_dept)

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
