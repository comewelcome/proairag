import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant_settings import TenantSettings
from src.schemas.settings import RagSettingsUpdate, RagSettingsResponse


class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_settings(self, tenant_id: uuid.UUID) -> RagSettingsResponse:
        result = await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        settings = result.scalar_one_or_none()

        if settings:
            return RagSettingsResponse.model_validate(settings)

        # Return defaults if no settings exist
        return RagSettingsResponse(
            chunk_size=512,
            chunk_overlap=64,
            top_k=5,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            openai_api_base="http://localhost:1234/v1",
        )

    async def update_settings(
        self, tenant_id: uuid.UUID, data: RagSettingsUpdate
    ) -> RagSettingsResponse:
        result = await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        settings = result.scalar_one_or_none()

        update_data = data.model_dump(exclude_none=True)

        if settings:
            for key, value in update_data.items():
                setattr(settings, key, value)
        else:
            settings = TenantSettings(
                tenant_id=tenant_id,
                **update_data,
            )
            self.db.add(settings)

        await self.db.commit()
        await self.db.refresh(settings)
        return RagSettingsResponse.model_validate(settings)

    async def get_system_stats(self, tenant_id: uuid.UUID) -> dict:
        from sqlalchemy import func
        from src.models.document import Document
        from src.models.chunk import Chunk

        doc_count_result = await self.db.execute(
            select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
        )
        chunk_count_result = await self.db.execute(
            select(func.count(Chunk.id)).where(Chunk.tenant_id == tenant_id)
        )

        # Check database connections
        postgres_ok = True
        neo4j_ok = True

        try:
            await self.db.execute(select(func.now()))
        except Exception:
            postgres_ok = False

        try:
            from src.graph.neo4j_client import get_neo4j_client
            client = get_neo4j_client()
            if client:
                await client.execute("RETURN 1")
        except Exception:
            neo4j_ok = False

        # Get Neo4j entity count
        entity_count = 0
        try:
            from src.graph.neo4j_client import get_neo4j_client
            client = get_neo4j_client()
            if client:
                result = await client.execute(
                    f"MATCH (e:Entity {{tenant_id: '{tenant_id}'}}) RETURN count(e)"
                )
                if result and len(result) > 0:
                    entity_count = int(str(result[0][0]))
        except Exception:
            pass

        return {
            "document_count": doc_count_result.scalar() or 0,
            "chunk_count": chunk_count_result.scalar() or 0,
            "entity_count": entity_count,
            "postgres_connected": postgres_ok,
            "neo4j_connected": neo4j_ok,
        }


def get_settings_service(db: AsyncSession) -> SettingsService:
    return SettingsService(db)
