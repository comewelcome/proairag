from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import TenantId
from src.services.auth_service import get_auth_service
from src.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = get_auth_service(db)
    user = await service.authenticate(data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = service.create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        is_tenant_admin=user.is_tenant_admin,
    )
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: UserCreate,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_auth_service(db)

    # Check if email already exists in tenant
    existing = await service.get_user_by_email(tenant_id, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered for this tenant",
        )

    user = await service.register_user(tenant_id, data)
    token = service.create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        is_tenant_admin=user.is_tenant_admin,
    )
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
