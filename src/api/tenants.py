from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.services.tenant_service import get_tenant_service
from src.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("/", response_model=TenantResponse, status_code=201)
async def create_tenant(data: TenantCreate, db: AsyncSession = Depends(get_db)):
    service = get_tenant_service(db)
    tenant = await service.create(data)
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id, db: AsyncSession = Depends(get_db)):
    service = get_tenant_service(db)
    tenant = await service.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
