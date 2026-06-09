import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import TenantId, UserId, IsTenantAdmin
from src.services.department_service import get_department_service
from src.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    UserDepartmentAssignment,
    UserDepartmentResponse,
)

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("/", response_model=list[DepartmentResponse])
async def list_departments(
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    return await service.list_by_tenant(tenant_id)


@router.post("/", response_model=DepartmentResponse, status_code=201)
async def create_department(
    data: DepartmentCreate,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    return await service.create(tenant_id, data)


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    dept = await service.get_by_id(department_id)
    if not dept or dept.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    data: DepartmentUpdate,
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    dept = await service.update(department_id, tenant_id, data)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.delete("/{department_id}", status_code=204)
async def delete_department(
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    if not await service.delete(department_id, tenant_id):
        raise HTTPException(status_code=404, detail="Department not found")


@router.post(
    "/{department_id}/users", response_model=UserDepartmentResponse, status_code=201
)
async def assign_user_to_department(
    data: UserDepartmentAssignment,
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    user_id: UserId = ...,  # type: ignore
    is_tenant_admin: IsTenantAdmin = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    # Only tenant admins can assign users to departments
    if not user_id or not is_tenant_admin:
        raise HTTPException(status_code=403, detail="Tenant admin required")

    service = get_department_service(db)
    ud = await service.assign_user(data.user_id, tenant_id, department_id, data.role)
    if not ud:
        raise HTTPException(status_code=404, detail="User or department not found")
    return ud


@router.delete("/{department_id}/users/{user_id}", status_code=204)
async def remove_user_from_department(
    user_id: uuid.UUID,
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    if not await service.remove_user(user_id, tenant_id, department_id):
        raise HTTPException(status_code=404, detail="Assignment not found")
