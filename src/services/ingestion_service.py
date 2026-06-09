import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.document import Document
from src.models.chunk import Chunk
from src.services.embedding_service import get_embedding_service
from src.config import get_settings


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()
        self.settings = get_settings()

    async def ingest_document(
        self,
        tenant_id: uuid.UUID,
        title: str,
        content: str,
        source: str | None = None,
        content_type: str = "text",
    ) -> Document:
        document = Document(
            tenant_id=tenant_id,
            title=title,
            content=content,
            source=source,
            content_type=content_type,
            is_processed=False,
        )
        self.db.add(document)
        await self.db.flush()

        chunks_text = self._chunk_text(content)
        embeddings = await self.embedding_service.embed_texts(chunks_text)

        for i, (text, embedding) in enumerate(zip(chunks_text, embeddings)):
            chunk = Chunk(
                tenant_id=tenant_id,
                document_id=document.id,
                content=text,
                embedding=embedding,
                chunk_index=i,
            )
            self.db.add(chunk)

        document.is_processed = True
        await self.db.commit()
        await self.db.refresh(document)
        return document

    def _chunk_text(self, text: str) -> list[str]:
        chunk_size = self.settings.chunk_size
        overlap = self.settings.chunk_overlap
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i : i + chunk_size]
            if chunk_words:
                chunks.append(" ".join(chunk_words))

        return chunks if chunks else [text]


def get_ingestion_service(db: AsyncSession) -> IngestionService:
    return IngestionService(db)
