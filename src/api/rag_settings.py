from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import TenantId
from src.services.settings_service import get_settings_service
from src.schemas.settings import RagSettingsUpdate, RagSettingsResponse, SystemStats

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/", response_model=RagSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    service = get_settings_service(db)
    return await service.get_settings(tenant_id)


@router.put("/", response_model=RagSettingsResponse)
async def update_settings(
    data: RagSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    service = get_settings_service(db)
    return await service.update_settings(tenant_id, data)


@router.get("/stats", response_model=SystemStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    service = get_settings_service(db)
    return await service.get_system_stats(tenant_id)
