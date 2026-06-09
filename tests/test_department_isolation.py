import pytest
from src.models.document import Document
from src.models.chunk import Chunk
from src.services.vector_service import get_vector_service


class TestDepartmentIsolation:
    """Tests CRITIQUES: isolation inter-departements.
    Un echec ici = fuite de donnees entre departements."""

    @pytest.mark.asyncio
    async def test_hr_cannot_see_compta_documents(
        self, tenant_a, dept_hr, dept_compta, db_session
    ):
        """Un utilisateur RH ne doit pas voir les documents de la comptabilite."""
        # Create a compta document
        compta_doc = Document(
            tenant_id=tenant_a.id,
            department_id=dept_compta.id,
            title="Paie employees",
            content="Salaires confidentiels",
        )
        db_session.add(compta_doc)
        await db_session.commit()
        await db_session.refresh(compta_doc)

        # Create a chunk
        chunk = Chunk(
            tenant_id=tenant_a.id,
            document_id=compta_doc.id,
            content="Salaire: 5000 EUR",
            embedding=[0.1] * 384,
            chunk_index=0,
        )
        db_session.add(chunk)
        await db_session.commit()

        # HR user should NOT see this in vector search
        vector_service = get_vector_service(db_session)
        hr_dept_ids = [dept_hr.id]
        results = await vector_service.search(
            query="salaire",
            tenant_id=tenant_a.id,
            department_ids=hr_dept_ids,
            is_tenant_admin=False,
        )
        assert all(r.get("document_id") != compta_doc.id for r in results)

    @pytest.mark.asyncio
    async def test_tenant_admin_sees_all_departments(
        self, tenant_a, dept_hr, dept_compta, db_session
    ):
        """Un tenant admin doit pouvoir voir les documents de tous les departements."""
        # Create HR document
        hr_doc = Document(
            tenant_id=tenant_a.id,
            department_id=dept_hr.id,
            title="Politique RH",
            content="Conges payes",
        )
        db_session.add(hr_doc)
        await db_session.commit()
        await db_session.refresh(hr_doc)

        chunk = Chunk(
            tenant_id=tenant_a.id,
            document_id=hr_doc.id,
            content="Politique de conges",
            embedding=[0.1] * 384,
            chunk_index=0,
        )
        db_session.add(chunk)
        await db_session.commit()

        # Compta user with is_tenant_admin=True should see HR docs
        vector_service = get_vector_service(db_session)
        results = await vector_service.search(
            query="conges",
            tenant_id=tenant_a.id,
            department_ids=[dept_compta.id],
            is_tenant_admin=True,
        )
        # Should find the HR document because admin bypasses dept filter
        assert any(r.get("document_id") == hr_doc.id for r in results)

    @pytest.mark.asyncio
    async def test_null_department_visible_to_all(
        self, tenant_a, dept_hr, db_session
    ):
        """Les documents sans departement sont visibles par tous les utilisateurs du tenant."""
        # Document with no department (backward compat)
        doc = Document(
            tenant_id=tenant_a.id,
            department_id=None,
            title="Document general",
            content="Visible par tous",
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        chunk = Chunk(
            tenant_id=tenant_a.id,
            document_id=doc.id,
            content="Document general",
            embedding=[0.1] * 384,
            chunk_index=0,
        )
        db_session.add(chunk)
        await db_session.commit()

        # Should be visible to any department user
        vector_service = get_vector_service(db_session)
        results = await vector_service.search(
            query="general",
            tenant_id=tenant_a.id,
            department_ids=[dept_hr.id],
            is_tenant_admin=False,
        )
        assert any(r.get("document_id") == doc.id for r in results)
