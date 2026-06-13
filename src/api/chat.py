import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import TenantId, UserId, IsTenantAdmin
from src.services.chat_service import get_chat_service
from src.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

router = APIRouter(prefix="/api/chat/sessions", tags=["chat"])


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_session(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    service = get_chat_service(db)
    return await service.create_conversation(
        tenant_id=tenant_id,
        title=data.title,
        department_id=data.department_id,
    )


@router.get("/", response_model=list[ConversationResponse])
async def list_sessions(
    department_id: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    dept_uuid = None
    if department_id:
        try:
            dept_uuid = uuid.UUID(department_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid department ID")
    service = get_chat_service(db)
    return await service.list_conversations(
        tenant_id=tenant_id,
        department_id=dept_uuid,
        limit=limit,
    )


@router.get("/{session_id}", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    try:
        conv_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    service = get_chat_service(db)
    conv = await service.get_conversation(conv_uuid, tenant_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Session not found")
    return await service.get_messages(conv_uuid, tenant_id)


@router.post("/{session_id}/send", response_model=MessageResponse)
async def send_message(
    session_id: str,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
    user_id: UserId = ...,  # type: ignore
    is_tenant_admin: IsTenantAdmin = ...,  # type: ignore
):
    try:
        conv_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    dept_uuid = None
    if data.department_id:
        try:
            dept_uuid = uuid.UUID(str(data.department_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid department ID")
    service = get_chat_service(db)
    return await service.send_message(
        conversation_id=conv_uuid,
        tenant_id=tenant_id,
        user_message=data.message,
        department_id=dept_uuid,
        user_id=user_id,
        is_tenant_admin=is_tenant_admin,
    )


@router.put("/{session_id}/title")
async def rename_session(
    session_id: str,
    title: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    from src.models.conversation import Conversation
    try:
        conv_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    conv = await db.get(Conversation, conv_uuid)
    if not conv or conv.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Session not found")
    conv.title = title[:256]
    await db.commit()
    return {"status": "renamed"}


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
):
    try:
        conv_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    service = get_chat_service(db)
    deleted = await service.delete_conversation(conv_uuid, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}
