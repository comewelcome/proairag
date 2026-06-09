import uuid
import pytest
from src.models.document import Document
from src.models.chunk import Chunk


class TestTenantIsolation:
    """
    Tests CRITIQUES: verifient que l'isolation multi-tenant fonctionne.
    Un echec ici = faille de securite.
    """

    @pytest.mark.asyncio
    async def test_chunks_have_tenant_id(self, tenant_a, tenant_b, db_session):
        doc = Document(
            tenant_id=tenant_a.id,
            title="Test doc",
            content="Test content",
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        chunk = Chunk(
            tenant_id=tenant_a.id,
            document_id=doc.id,
            content="Test chunk",
            embedding=[0.1] * 384,
            chunk_index=0,
        )
        db_session.add(chunk)
        await db_session.commit()

        assert chunk.tenant_id == tenant_a.id
        assert chunk.tenant_id != tenant_b.id

    @pytest.mark.asyncio
    async def test_documents_have_tenant_id(self, tenant_a, tenant_b, db_session):
        doc = Document(
            tenant_id=tenant_a.id,
            title="Secret de A",
            content="Information confidentielle du tenant A",
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        assert doc.tenant_id == tenant_a.id
        assert doc.tenant_id != tenant_b.id


class TestAPIKeyAuth:
    """Tests d'authentification par API key."""

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self, client):
        response = await client.post(
            "/documents/",
            json={"title": "t", "content": "c"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_403(self, client):
        response = await client.post(
            "/documents/",
            json={"title": "t", "content": "c"},
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_health_without_api_key(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
