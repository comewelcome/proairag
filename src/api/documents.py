import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import TenantId
from src.models.document import Document
from src.models.chunk import Chunk
from src.services.ingestion_service import get_ingestion_service
from src.schemas.document import DocumentCreate, DocumentResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    department_id: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    """List documents for the current tenant, optionally filtered by department."""
    query = select(Document).where(
        Document.tenant_id == tenant_id
    ).order_by(Document.created_at.desc()).limit(limit)

    if department_id:
        try:
            dept_uuid = uuid.UUID(department_id)
            query = query.where(Document.department_id == dept_uuid)
        except ValueError:
            pass

    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    """Delete a document and its chunks."""
    try:
        doc_uuid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    # Delete chunks first
    await db.execute(
        sa_delete(Chunk).where(Chunk.document_id == doc_uuid)
    )

    doc = await db.get(Document, doc_uuid)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.delete(doc)
    await db.commit()
    return {"status": "deleted"}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document_file(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    department_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    """Upload a file (PDF, TXT, DOCX, CSV) and ingest it."""
    # Read file content
    content_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # Parse based on content type
    doc_title = title or file.filename or "Untitled"
    max_size = 50 * 1024 * 1024  # 50MB
    if len(content_bytes) > max_size:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    text_content = _parse_file_content(content_bytes, content_type, file.filename)

    dept_uuid = None
    if department_id:
        try:
            dept_uuid = uuid.UUID(department_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid department ID")

    service = get_ingestion_service(db)
    document = await service.ingest_document(
        tenant_id=tenant_id,
        title=doc_title,
        content=text_content,
        source=file.filename,
        content_type=content_type,
        department_id=dept_uuid,
    )
    return document


def _parse_file_content(data: bytes, content_type: str, filename: str | None) -> str:
    """Parse file content to text based on type."""
    fn = filename or ""
    ct = (content_type or "").lower()

    # Try LiteParse for PDF
    if "pdf" in ct or fn.endswith(".pdf"):
        try:
            from liteparse import LiteParse
            parser = LiteParse(ocr_enabled=False)
            result = parser.parse(data)
            return result.text or "(empty PDF)"
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="PDF parsing requires liteparse. Install with: pip install liteparse"
            )

    # Try python-docx for DOCX
    if "word" in ct or "docx" in ct or fn.endswith(".docx"):
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument.load(data)
            text = "\n".join(p.text for p in doc.paragraphs)
            return text or "(empty document)"
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="DOCX parsing requires python-docx. Install with: pip install python-docx"
            )

    # Text-based files
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Could not decode file as text"
            )
