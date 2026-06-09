from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import TenantId
from src.services.ingestion_service import get_ingestion_service
from src.schemas.document import DocumentCreate, DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse)
async def upload_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    service = get_ingestion_service(db)
    document = await service.ingest_document(
        tenant_id=tenant_id,
        title=data.title,
        content=data.content,
        source=data.source,
        content_type=data.content_type,
        department_id=data.department_id,
    )
    return document
