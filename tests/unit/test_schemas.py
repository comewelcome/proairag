"""Unit tests for Pydantic schemas (validation, serialization)."""

import uuid
from datetime import datetime

import pytest

from src.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from src.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    UserDepartmentAssignment,
    UserDepartmentResponse,
)
from src.schemas.document import DocumentCreate, DocumentResponse
from src.schemas.rag import RAGQuery, RAGResponse, RAGSource
from src.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate


class TestUserCreateSchema:
    """Tests pour le schema UserCreate."""

    def test_valid_user_create(self):
        """UserCreate valide avec tous les champs."""
        user = UserCreate(
            email="test@example.com",
            password="secure_password_123",
            full_name="Test User",
        )

        assert user.email == "test@example.com"
        assert user.password == "secure_password_123"
        assert user.full_name == "Test User"

    def test_user_create_minimal(self):
        """UserCreate avec juste les champs requis."""
        user = UserCreate(
            email="test@example.com",
            password="secure_password_123",
        )

        assert user.full_name is None

    def test_user_create_empty_email_fails(self):
        """UserCreate echoue avec un email vide."""
        with pytest.raises(Exception):
            UserCreate(
                email="",
                password="secure_password_123",
            )

    def test_user_create_short_password_fails(self):
        """UserCreate echoue avec un mot de passe trop court."""
        with pytest.raises(Exception):
            UserCreate(
                email="test@example.com",
                password="short",
            )

    def test_user_create_max_length_email(self):
        """UserCreate accepte un email de 255 caracteres."""
        long_email = "a" * 200 + "@example.com"
        user = UserCreate(
            email=long_email,
            password="secure_password_123",
        )

        assert len(user.email) == 212


class TestLoginRequestSchema:
    """Tests pour le schema LoginRequest."""

    def test_valid_login(self):
        """LoginRequest valide."""
        login = LoginRequest(
            email="test@example.com",
            password="password123",
        )

        assert login.email == "test@example.com"
        assert login.password == "password123"

    def test_login_empty_email_fails(self):
        """LoginRequest echoue avec un email vide."""
        with pytest.raises(Exception):
            LoginRequest(
                email="",
                password="password123",
            )


class TestTokenResponseSchema:
    """Tests pour le schema TokenResponse."""

    def test_valid_token_response(self):
        """TokenResponse valide."""
        token = TokenResponse(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            user=UserResponse(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                email="test@example.com",
                full_name="Test User",
                is_tenant_admin=False,
                is_active=True,
                created_at=datetime.now(),
            ),
        )

        assert token.token_type == "bearer"
        assert token.user.email == "test@example.com"


class TestDepartmentSchemas:
    """Tests pour les schemas Department."""

    def test_department_create(self):
        """DepartmentCreate valide."""
        dept = DepartmentCreate(name="RH", description="Ressources Humaines")

        assert dept.name == "RH"
        assert dept.description == "Ressources Humaines"

    def test_department_create_minimal(self):
        """DepartmentCreate avec juste le nom."""
        dept = DepartmentCreate(name="IT")

        assert dept.name == "IT"
        assert dept.description is None

    def test_department_create_empty_name_fails(self):
        """DepartmentCreate echoue avec un nom vide."""
        with pytest.raises(Exception):
            DepartmentCreate(name="")

    def test_department_response(self):
        """DepartmentResponse valide."""
        dept_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        dept = DepartmentResponse(
            id=dept_id,
            tenant_id=tenant_id,
            name="RH",
            description="Ressources Humaines",
            created_at=datetime.now(),
        )

        assert dept.id == dept_id
        assert dept.name == "RH"

    def test_department_update(self):
        """DepartmentUpdate avec champs optionnels."""
        update = DepartmentUpdate(name="RH Update")

        assert update.name == "RH Update"
        assert update.description is None

    def test_department_update_empty(self):
        """DepartmentUpdate sans champs."""
        update = DepartmentUpdate()

        assert update.name is None
        assert update.description is None


class TestUserDepartmentAssignment:
    """Tests pour le schema UserDepartmentAssignment."""

    def test_valid_assignment_member(self):
        """Assignment valide avec role member."""
        assignment = UserDepartmentAssignment(
            user_id=uuid.uuid4(),
            role="member",
        )

        assert assignment.role == "member"

    def test_valid_assignment_admin(self):
        """Assignment valide avec role admin."""
        assignment = UserDepartmentAssignment(
            user_id=uuid.uuid4(),
            role="admin",
        )

        assert assignment.role == "admin"

    def test_invalid_role_fails(self):
        """Assignment echoue avec un role invalide."""
        with pytest.raises(Exception):
            UserDepartmentAssignment(
                user_id=uuid.uuid4(),
                role="superadmin",
            )

    def test_assignment_default_role(self):
        """Assignment avec role par defaut."""
        assignment = UserDepartmentAssignment(user_id=uuid.uuid4())

        assert assignment.role == "member"


class TestDocumentSchemas:
    """Tests pour les schemas Document."""

    def test_document_create(self):
        """DocumentCreate valide."""
        doc = DocumentCreate(
            title="Test Document",
            content="Content of the document",
            source="test.pdf",
            content_type="text",
            department_id=uuid.uuid4(),
        )

        assert doc.title == "Test Document"
        assert doc.content == "Content of the document"
        assert doc.source == "test.pdf"
        assert doc.content_type == "text"
        assert doc.department_id is not None

    def test_document_create_minimal(self):
        """DocumentCreate avec juste les champs requis."""
        doc = DocumentCreate(
            title="Test Document",
            content="Content",
        )

        assert doc.source is None
        assert doc.content_type == "text"
        assert doc.department_id is None

    def test_document_create_empty_title_fails(self):
        """DocumentCreate echoue avec un titre vide."""
        with pytest.raises(Exception):
            DocumentCreate(
                title="",
                content="Content",
            )

    def test_document_create_empty_content_fails(self):
        """DocumentCreate echoue avec un contenu vide."""
        with pytest.raises(Exception):
            DocumentCreate(
                title="Title",
                content="",
            )

    def test_document_response(self):
        """DocumentResponse valide."""
        doc_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        dept_id = uuid.uuid4()

        doc = DocumentResponse(
            id=doc_id,
            tenant_id=tenant_id,
            department_id=dept_id,
            title="Test Document",
            source="test.pdf",
            content_type="text",
            is_processed=True,
            created_at=datetime.now(),
        )

        assert doc.id == doc_id
        assert doc.department_id == dept_id
        assert doc.is_processed is True


class TestRAGSchemas:
    """Tests pour les schemas RAG."""

    def test_rag_query_default(self):
        """RAGQuery avec valeurs par defaut."""
        query = RAGQuery(query="What is the company policy?")

        assert query.query == "What is the company policy?"
        assert query.top_k == 5
        assert query.include_graph_context is True
        assert query.graph_depth == 2

    def test_rag_query_custom(self):
        """RAGQuery avec valeurs personnalisees."""
        query = RAGQuery(
            query="What is the company policy?",
            top_k=10,
            include_graph_context=False,
            graph_depth=3,
        )

        assert query.top_k == 10
        assert query.include_graph_context is False
        assert query.graph_depth == 3

    def test_rag_query_top_k_limits(self):
        """RAGQuery respecte les limites de top_k."""
        # Valid top_k
        query = RAGQuery(query="Test", top_k=1)
        assert query.top_k == 1

        query = RAGQuery(query="Test", top_k=20)
        assert query.top_k == 20

        # Invalid top_k (too low)
        with pytest.raises(Exception):
            RAGQuery(query="Test", top_k=0)

        # Invalid top_k (too high)
        with pytest.raises(Exception):
            RAGQuery(query="Test", top_k=21)

    def test_rag_query_empty_query_fails(self):
        """RAGQuery echoue avec une requete vide."""
        with pytest.raises(Exception):
            RAGQuery(query="")

    def test_rag_source(self):
        """RAGSource valide."""
        source = RAGSource(
            content="Sample content from a document",
            source_type="vector",
            similarity=0.85,
            document_id=str(uuid.uuid4()),
            document_title="Test Document",
        )

        assert source.source_type == "vector"
        assert source.similarity == 0.85

    def test_rag_response(self):
        """RAGResponse valide."""
        response = RAGResponse(
            answer="The company policy is to work from home.",
            sources=[
                RAGSource(
                    content="Policy content...",
                    source_type="vector",
                    similarity=0.9,
                )
            ],
            graph_context=[{"entity": "Company", "related": "Policy"}],
            query_entities=["Company", "Policy"],
        )

        assert response.answer == "The company policy is to work from home."
        assert len(response.sources) == 1
        assert response.graph_context is not None
        assert response.query_entities is not None


class TestTenantSchemas:
    """Tests pour les schemas Tenant."""

    def test_tenant_create(self):
        """TenantCreate valide."""
        tenant = TenantCreate(name="Acme Corp")

        assert tenant.name == "Acme Corp"
        assert tenant.api_key is None
        assert tenant.admin_email is None
        assert tenant.admin_password is None
        assert tenant.admin_full_name is None

    def test_tenant_create_with_admin(self):
        """TenantCreate avec admin user."""
        tenant = TenantCreate(
            name="Acme Corp",
            admin_email="admin@acme.com",
            admin_password="secure_password_123",
            admin_full_name="Admin User",
        )

        assert tenant.admin_email == "admin@acme.com"
        assert tenant.admin_full_name == "Admin User"

    def test_tenant_create_empty_name_fails(self):
        """TenantCreate echoue avec un nom vide."""
        with pytest.raises(Exception):
            TenantCreate(name="")

    def test_tenant_response(self):
        """TenantResponse valide."""
        tenant_id = uuid.uuid4()

        tenant = TenantResponse(
            id=tenant_id,
            name="Acme Corp",
            is_active=True,
            created_at=datetime.now(),
        )

        assert tenant.id == tenant_id
        assert tenant.name == "Acme Corp"
        assert tenant.is_active is True

    def test_tenant_update(self):
        """TenantUpdate avec champs optionnels."""
        update = TenantUpdate(name="New Name", is_active=False)

        assert update.name == "New Name"
        assert update.is_active is False

    def test_tenant_update_empty(self):
        """TenantUpdate sans champs."""
        update = TenantUpdate()

        assert update.name is None
        assert update.is_active is None
        assert update.api_key is None
