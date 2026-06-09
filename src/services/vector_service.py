import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.embedding_service import get_embedding_service
from src.config import get_settings


class VectorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()

    async def search(
        self,
        query: str,
        tenant_id: uuid.UUID,
        top_k: int | None = None,
    ) -> list[dict]:
        if top_k is None:
            top_k = get_settings().top_k

        query_embedding = await self.embedding_service.embed_text(query)
        embedding_str = self._embedding_to_string(query_embedding)

        result = await self.db.execute(
            text("""
                SELECT
                    c.id,
                    c.content,
                    c.chunk_index,
                    c.document_id,
                    d.title as document_title,
                    1 - (c.embedding <=> :embedding::vector) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.tenant_id = :tenant_id
                ORDER BY c.embedding <=> :embedding::vector
                LIMIT :top_k
            """),
            {
                "embedding": embedding_str,
                "tenant_id": str(tenant_id),
                "top_k": top_k,
            },
        )

        rows = result.mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def _embedding_to_string(embedding: list[float]) -> str:
        return "[" + ",".join(str(x) for x in embedding) + "]"


def get_vector_service(db: AsyncSession) -> VectorService:
    return VectorService(db)
