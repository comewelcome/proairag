from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import TenantId, UserId, IsTenantAdmin
from src.services.rag_service import get_rag_service
from src.schemas.rag import RAGQuery, RAGResponse

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/query", response_model=RAGResponse)
async def rag_query(
    query: RAGQuery,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
    user_id: UserId = ...,  # type: ignore
    is_tenant_admin: IsTenantAdmin = ...,  # type: ignore
):
    service = get_rag_service(db)
    result = await service.query(
        tenant_id=tenant_id,
        rag_query=query,
        user_id=user_id,
        is_tenant_admin=is_tenant_admin,
    )
    return result
