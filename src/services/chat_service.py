import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.conversation import Conversation
from src.models.message import Message
from src.services.rag_service import get_rag_service
from src.schemas.chat import ConversationResponse, MessageResponse


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(
        self,
        tenant_id: uuid.UUID,
        title: str = "Nouvelle conversation",
        department_id: uuid.UUID | None = None,
    ) -> ConversationResponse:
        conversation = Conversation(
            tenant_id=tenant_id,
            title=title,
            department_id=department_id,
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return ConversationResponse.model_validate(conversation)

    async def list_conversations(
        self,
        tenant_id: uuid.UUID,
        department_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ConversationResponse]:
        query = select(Conversation).where(
            Conversation.tenant_id == tenant_id
        ).order_by(Conversation.updated_at.desc()).limit(limit)

        if department_id:
            query = query.where(Conversation.department_id == department_id)

        result = await self.db.execute(query)
        conversations = result.scalars().all()
        return [ConversationResponse.model_validate(c) for c in conversations]

    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ConversationResponse | None:
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            return None
        return ConversationResponse.model_validate(conv)

    async def get_messages(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[MessageResponse]:
        # Verify conversation belongs to tenant
        conv = await self.db.get(Conversation, conversation_id)
        if not conv or conv.tenant_id != tenant_id:
            return []

        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        return [MessageResponse.model_validate(m) for m in messages]

    async def send_message(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_message: str,
        department_id: uuid.UUID | None = None,
        top_k: int = 5,
    ) -> MessageResponse:
        # Verify conversation belongs to tenant
        conv = await self.db.get(Conversation, conversation_id)
        if not conv or conv.tenant_id != tenant_id:
            raise ValueError("Conversation not found")

        # Save user message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(user_msg)

        # Get RAG response
        from src.schemas.rag import RAGQuery
        rag_service = get_rag_service(self.db)

        try:
            rag_result = await rag_service.query(
                tenant_id=tenant_id,
                rag_query=RAGQuery(
                    query=user_message,
                    top_k=top_k,
                    include_graph_context=True,
                    graph_depth=2,
                ),
                is_tenant_admin=True,
            )
            assistant_content = rag_result.answer
            sources = []
            for s in (rag_result.sources or []):
                if s.source_type == "vector":
                    sources.append({
                        "doc_id": s.document_id or "",
                        "doc_title": s.document_title or "Unknown",
                        "score": s.similarity or 0,
                    })
            graph_context = rag_result.graph_context or []
        except Exception:
            assistant_content = f"Je ne trouve pas de reponses dans les documents pour : {user_message}"
            sources = []
            graph_context = []

        # Update conversation title from first message
        if conv.title == "Nouvelle conversation":
            conv.title = user_message[:100]
            conv.updated_at = datetime.now(timezone.utc)

        # Save assistant message
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            sources=sources,
            graph_context=graph_context,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(assistant_msg)

        await self.db.commit()
        await self.db.refresh(assistant_msg)
        return MessageResponse.model_validate(assistant_msg)

    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        conv = await self.db.get(Conversation, conversation_id)
        if not conv or conv.tenant_id != tenant_id:
            return False
        await self.db.delete(conv)
        await self.db.commit()
        return True

    async def get_stats(self, tenant_id: uuid.UUID) -> dict:
        """Get conversation and stats data for the tenant."""
        # Document count
        from src.models.document import Document
        doc_result = await self.db.execute(
            select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
        )
        doc_count = doc_result.scalar()

        # Chunk count
        from src.models.chunk import Chunk
        chunk_result = await self.db.execute(
            select(func.count(Chunk.id)).where(Chunk.tenant_id == tenant_id)
        )
        chunk_count = chunk_result.scalar()

        return {
            "document_count": doc_count or 0,
            "chunk_count": chunk_count or 0,
        }


def get_chat_service(db: AsyncSession) -> ChatService:
    return ChatService(db)
