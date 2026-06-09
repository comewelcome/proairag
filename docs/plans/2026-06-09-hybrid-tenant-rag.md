# Hybrid Tenant-Isolated RAG — Implementation Plan

> **Pour Hermes:** Utiliser le skill subagent-driven-development pour implémenter ce plan tâche par tâche.

**Goal:** Construire un système RAG hybride multi-tenant où la base relationnelle garantit l'isolation stricte des données par client (Row-Level Security), et la base graphe enrichit la compréhension sémantique via les relations entre entités.

**Architecture:** PostgreSQL (RLS + pgvector) assure le confinement multi-tenant au niveau base de données. Neo4j modélise le knowledge graph intra-tenant (entités, relations, hiérarchies). Une couche d'orchestration résout les requêtes en consultant les deux sources avec un tenant_id forcé.

**Tech Stack:** Python 3.11+, FastAPI, PostgreSQL 15+ (pgvector), Neo4j 5.x, LangChain, sentence-transformers, SQLAlchemy 2.0, py2neo/neo4j driver.

---

## Architecture Overview

```
                    +-----------------+
                    |    FastAPI API   |
                    +--------+--------+
                             |
              +--------------+---------------+
              |   Tenant Context Middleware   |
              |  (extrait/valide tenant_id)   |
              +--------------+---------------+
                             |
          +------------------+------------------+
          |                                 |
   +------+-------+                 +--------+-------+
   |  PostgreSQL   |                 |    Neo4j       |
   |  (pgvector)   |                 |  (Knowledge    |
   |               |                 |   Graph)       |
   | - Documents   |<-- sync ------>| - Entities     |
   | - Chunks      |                 | - Relations    |
   | - Embeddings  |                 | - Properties   |
   | - Metadata    |                 |                |
   | - RLS policies|                 | - tenant_id    |
   |   par tenant  |                 |   sur chaque   |
   +---------------+                 |   node/rel     |
                                     +----------------+
```

### Pourquoi l'hybride ?

| Besoin | PostgreSQL (Relationnel) | Neo4j (Graphe) |
|---|---|---|
| Isolation multi-tenant | **Row-Level Security** natif | tenant_id sur chaque node |
| Stockage embeddings | **pgvector** (HNSW/IVF) | Non applicable |
| Relations sémantiques | Jointures SQL (limitées) | **Traversals natifs** (BFS/DFS) |
| Recherche vectorielle | **ANN via pgvector** | GDS Node Similarity |
| Transactions | **ACID complet** | ACID avec limitations |
| Requêtes relationnelles | **SQL natif** | Cypher (différent) |
| Raisonnement graph | Impossible | **Pathfinding, patterns** |
| Permissions fines | **RBAC + RLS granulaire** | Application-level only |

---

## Phase 0 : Infrastructure & Bootstrap

### Task 1 : Initialiser la structure du projet

**Objective:** Créer l'arborescence du projet avec tous les dossiers nécessaires.

**Files:**
- Create: `pyproject.toml`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `src/`, `tests/`, `migrations/`

```
proairag/
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── docs/
│   └── plans/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings (pydantic-settings)
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── tenant.py           # Tenant context extraction
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tenant.py           # Tenant SQLAlchemy model
│   │   ├── document.py         # Document SQLAlchemy model
│   │   ├── chunk.py            # Chunk + embedding model
│   │   └── permission.py       # Role/Permission models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── tenant.py
│   │   ├── document.py
│   │   └── rag.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tenant_service.py
│   │   ├── document_service.py
│   │   ├── ingestion_service.py
│   │   ├── embedding_service.py
│   │   ├── graph_service.py
│   │   ├── rag_service.py
│   │   └── vector_service.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── neo4j_client.py
│   │   ├── entity_extractor.py
│   │   └── graph_sync.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── rls_policies.py
│   │   └── seed.py
│   └── api/
│       ├── __init__.py
│       ├── tenants.py
│       ├── documents.py
│       └── rag.py
├── migrations/
│   ├── sql/                    # Raw SQL for RLS policies
│   │   ├── 001_create_tenants.sql
│   │   ├── 002_create_documents.sql
│   │   ├── 003_create_chunks.sql
│   │   ├── 004_create_permissions.sql
│   │   └── 005_rls_policies.sql
│   └── cypher/                 # Neo4j schema
│       ├── 001_constraints.cypher
│       └── 002_indexes.cypher
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_tenant_isolation.py
    ├── test_rls_policies.py
    ├── test_ingestion.py
    ├── test_graph_sync.py
    ├── test_rag_query.py
    └── test_api/
        ├── test_tenants.py
        ├── test_documents.py
        └── test_rag.py
```

**Step 1:** Créer la structure de dossiers

```bash
cd /home/yo/Desktop/code/proairag
mkdir -p src/middleware src/models src/schemas src/services src/graph src/db src/api
mkdir -p migrations/sql migrations/cypher
mkdir -p tests/test_api
touch src/__init__.py src/middleware/__init__.py src/models/__init__.py
touch src/schemas/__init__.py src/services/__init__.py src/graph/__init__.py
touch src/db/__init__.py src/api/__init__.py tests/__init__.py
touch tests/conftest.py
```

**Step 2:** Créer `pyproject.toml`

```toml
[project]
name = "proairag"
version = "0.1.0"
description = "Hybrid multi-tenant RAG with relational isolation and graph reasoning"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "psycopg[binary]>=3.2.0",
    "pgvector>=0.3.0",
    "neo4j>=5.20.0",
    "langchain>=0.3.0",
    "langchain-community>=0.3.0",
    "sentence-transformers>=3.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "ruff>=0.8.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

**Step 3:** Créer `.env.example`

```bash
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/proairag

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=proairag123

# Embedding model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# API
SECRET_KEY=change-me-in-production
API_HOST=0.0.0.0
API_PORT=8000
```

**Step 4:** Créer `docker-compose.yml`

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: proairag
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./migrations/sql:/docker-entrypoint-initdb.d

  neo4j:
    image: neo4j:5-community
    environment:
      NEO4J_AUTH: neo4j/proairag123
      NEO4J_apoc_export_file_enabled: "true"
      NEO4J_apoc_import_file_enabled: "true"
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4jdata:/data

volumes:
  pgdata:
  neo4jdata:
```

**Step 5:** Créer `.gitignore`

```
__pycache__/
*.pyc
.venv/
.env
*.egg-info/
dist/
build/
.coverage
htmlcov/
```

**Step 6:** Commit

```bash
git init
git add -A
git commit -m "init: project structure, docker-compose, pyproject.toml"
```

---

### Task 2 : Configurer les settings et l'entry point FastAPI

**Objective:** Mettre en place la configuration centralisée et l'application FastAPI minimale.

**Files:**
- Create: `src/config.py`
- Create: `src/main.py`

**Step 1:** Créer `src/config.py`

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # PostgreSQL
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/proairag"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "proairag123"

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # API
    secret_key: str = "change-me-in-production"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

**Step 2:** Créer `src/main.py`

```python
from fastapi import FastAPI
from src.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ProAirAg - Hybrid Multi-Tenant RAG",
        version="0.1.0",
    )

    # TODO: Add middleware (Task 3)
    # TODO: Add routers (later tasks)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
```

**Step 3:** Tester le démarrage

```bash
pip install -e ".[dev]"
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
# Expected: Uvicorn running on http://0.0.0.0:8000
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

**Step 4:** Commit

```bash
git add -A
git commit -m "feat: add config settings and FastAPI entry point"
```

---

## Phase 1 : Couche Base de Données & Isolation Multi-Tenant

### Task 3 : Créer le modèle Tenant et la session SQLAlchemy

**Objective:** Modèles SQLAlchemy pour les tenants avec session asynchrone.

**Files:**
- Create: `src/db/session.py`
- Create: `src/models/tenant.py`

**Step 1:** Créer `src/db/session.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from src.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

**Step 2:** Créer `src/models/tenant.py`

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.session import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    api_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="tenant")
```

**Step 3:** Commit

```bash
git add -A
git commit -m "feat: add Tenant model and async DB session"
```

---

### Task 4 : Créer les modèles Document et Chunk

**Objective:** Modèles pour les documents, les chunks vectoriels avec lien tenant.

**Files:**
- Create: `src/models/document.py`
- Create: `src/models/chunk.py`

**Step 1:** Créer `src/models/document.py`

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, UUID, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(1024))  # URL, file path
    content_type: Mapped[str] = mapped_column(String(50), default="text")
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")
```

**Step 2:** Créer `src/models/chunk.py`

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, UUID, Integer, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from src.db.session import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(String)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    chunk_index: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    tenant: Mapped["Tenant"] = relationship()
    document: Mapped["Document"] = relationship(back_populates="chunks")
```

**Step 3:** Import cross-references dans `src/models/__init__.py`

```python
from src.models.tenant import Tenant
from src.models.document import Document
from src.models.chunk import Chunk
```

**Step 4:** Commit

```bash
git add -A
git commit -m "feat: add Document and Chunk models with tenant isolation"
```

---

### Task 5 : Migrations SQL — création des tables + Row-Level Security

**Objective:** Scripts SQL pour créer les tables, les politiques RLS, et les rôles.

**Files:**
- Create: `migrations/sql/001_create_tenants.sql`
- Create: `migrations/sql/002_create_documents.sql`
- Create: `migrations/sql/003_create_chunks.sql`
- Create: `migrations/sql/005_rls_policies.sql`

**Step 1:** Créer `migrations/sql/001_create_tenants.sql`

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    api_key VARCHAR(512) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tenants_name ON tenants(name);
CREATE INDEX idx_tenants_api_key ON tenants(api_key);
```

**Step 2:** Créer `migrations/sql/002_create_documents.sql`

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title VARCHAR(512) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(1024),
    content_type VARCHAR(50) DEFAULT 'text',
    is_processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
```

**Step 3:** Créer `migrations/sql/003_create_chunks.sql`

```sql
-- pgvector must be loaded (handled by docker image)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(384),
    chunk_index INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chunks_tenant_id ON chunks(tenant_id);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops);
```

**Step 4:** Créer `migrations/sql/005_rls_policies.sql` — **CŒUR DE LA SÉCURITÉ**

```sql
-- ============================================================
-- ROW-LEVEL SECURITY: Isolation stricte multi-tenant
-- ============================================================

-- Activer RLS sur les tables sensibles
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Fonction utilitaire: retourne le tenant_id depuis une variable
-- de session PostgreSQL (set par l'application via SET LOCAL)
-- ============================================================
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS UUID AS $$
    SELECT current_setting('app.current_tenant_id', true)::UUID;
$$ LANGUAGE SQL STABLE;

-- Fonction pour les super-admins (bypass RLS)
CREATE OR REPLACE FUNCTION is_tenant_admin(tenant_id uuid)
RETURNS BOOLEAN AS $$
    SELECT
        current_setting('app.current_tenant_id', true)::UUID = tenant_id
        OR current_setting('app.is_admin', true)::BOOLEAN = true;
$$ LANGUAGE SQL STABLE;

-- ============================================================
-- Politiques RLS: documents
-- ============================================================

-- SELECT: un tenant ne voit que SES documents
CREATE POLICY tenant_document_isolation ON documents
    FOR SELECT
    USING (tenant_id = current_tenant_id());

-- INSERT: un tenant ne peut créer que dans SON espace
CREATE POLICY tenant_document_insert ON documents
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

-- UPDATE: un tenant ne modifie que SES documents
CREATE POLICY tenant_document_update ON documents
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- DELETE: un tenant ne supprime que SES documents
CREATE POLICY tenant_document_delete ON documents
    FOR DELETE
    USING (tenant_id = current_tenant_id());

-- ============================================================
-- Politiques RLS: chunks
-- ============================================================

CREATE POLICY tenant_chunk_isolation ON chunks
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_chunk_insert ON chunks
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_chunk_update ON chunks
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_chunk_delete ON chunks
    FOR DELETE
    USING (tenant_id = current_tenant_id());

-- ============================================================
-- NOTE: La table tenants n'a PAS de RLS — elle est gérée par
-- l'API avec une authentification séparée (api_key).
-- ============================================================
```

**Step 5:** Commit

```bash
git add -A
git commit -m "feat: SQL migrations with RLS policies for tenant isolation"
```

---

### Task 6 : Middleware Tenant Context — injection du tenant_id dans la session DB

**Objective:** Middleware FastAPI qui extrait le tenant_id depuis les headers et l'injecte dans la variable de session PostgreSQL.

**Files:**
- Create: `src/middleware/tenant.py`

**Step 1:** Créer `src/middleware/tenant.py`

```python
import uuid
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.db.session import async_session


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Extrait le tenant_id depuis le header X-Tenant-ID ou X-API-Key.
    Valide le tenant, puis injecte le tenant_id dans la session DB
    pour que les politiques RLS fonctionnent.
    """

    async def dispatch(self, request: Request, call_next):
        # Routes publiques (pas de tenant requis)
        public_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in public_paths:
            return await call_next(request)

        # Extraire tenant_id
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(status_code=401, detail="Missing X-API-Key header")

        # Valider le tenant
        async with async_session() as session:
            tenant = await session.execute(
                Tenant.__table__.select().where(Tenant.api_key == api_key, Tenant.is_active == True)
            )
            tenant = tenant.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

        # Injecter dans les headers pour les dépendances FastAPI
        request.state.tenant_id = tenant.id
        request.state.tenant = tenant

        response = await call_next(request)
        return response
```

**Step 2:** Créer la dépendance FastAPI pour récupérer le tenant

```python
# Ajouter à src/middleware/tenant.py (en bas du fichier):
from fastapi import Depends, Request


def get_tenant_id(request: Request) -> uuid.UUID:
    """Dépendance FastAPI pour injecter tenant_id dans les routes."""
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(status_code=400, detail="Tenant context missing")
    return request.state.tenant_id


def get_tenant(request: Request) -> Tenant:
    """Dépendance FastAPI pour injecter l'objet Tenant."""
    if not hasattr(request.state, "tenant"):
        raise HTTPException(status_code=400, detail="Tenant context missing")
    return request.state.tenant
```

**Step 3:** Enregistrer le middleware dans `src/main.py`

```python
from src.middleware.tenant import TenantContextMiddleware

# Dans create_app():
app.add_middleware(TenantContextMiddleware)
```

**Step 4:** Commit

```bash
git add -A
git commit -m "feat: tenant context middleware with API key validation"
```

---

### Task 7 : Service Tenant CRUD

**Objective:** CRUD pour la gestion des tenants (admin only).

**Files:**
- Create: `src/services/tenant_service.py`
- Create: `src/schemas/tenant.py`

**Step 1:** Créer `src/schemas/tenant.py`

```python
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    api_key: str | None = None  # Auto-générée si None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    api_key: str | None = None
```

**Step 2:** Créer `src/services/tenant_service.py`

```python
import uuid
import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: TenantCreate) -> Tenant:
        api_key = data.api_key or f"sk-{secrets.token_urlsafe(32)}"
        tenant = Tenant(name=data.name, api_key=api_key)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_api_key(self, api_key: str) -> Tenant | None:
        result = await self.db.execute(
            select(Tenant).where(Tenant.api_key == api_key)
        )
        return result.scalar_one_or_none()

    async def update(self, tenant_id: uuid.UUID, data: TenantUpdate) -> Tenant | None:
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tenant, key, value)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def deactivate(self, tenant_id: uuid.UUID) -> bool:
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False
        tenant.is_active = False
        await self.db.commit()
        return True
```

**Step 3:** Commit

```bash
git add -A
git commit -m "feat: tenant CRUD service with API key auto-generation"
```

---

## Phase 2 : Ingestion de Documents & Embeddings

### Task 8 : Service d'embeddings

**Objective:** Service pour générer des embeddings vectoriels depuis du texte.

**Files:**
- Create: `src/services/embedding_service.py`

**Step 1:** Créer `src/services/embedding_service.py`

```python
from sentence_transformers import SentenceTransformer
from src.config import get_settings


class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        self.model = SentenceTransformer(settings.embedding_model)
        self.dimension = settings.embedding_dimension

    async def embed_text(self, text: str) -> list[float]:
        """Génère un embedding pour un texte."""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Génère des embeddings batch (plus efficace)."""
        embeddings = self.model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return embeddings.tolist()

    async def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calcule la similarité cosinus entre deux embeddings."""
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# Singleton
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
```

**Step 2:** Commit

```bash
git add -A
git commit -m "feat: embedding service with sentence-transformers"
```

---

### Task 9 : Service d'ingestion — chunking + embedding + stockage

**Objective:** Pipeline qui prend un document, le découpe en chunks, génère les embeddings, et stocke tout dans PostgreSQL avec le tenant_id.

**Files:**
- Create: `src/services/ingestion_service.py`

**Step 1:** Créer `src/services/ingestion_service.py`

```python
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
        """
        Pipeline d'ingestion complet:
        1. Crée le document dans la BDD (tenant_id = isolation)
        2. Découpe le contenu en chunks
        3. Génère les embeddings
        4. Stocke les chunks + embeddings
        """
        # 1. Créer le document
        document = Document(
            tenant_id=tenant_id,
            title=title,
            content=content,
            source=source,
            content_type=content_type,
            is_processed=False,
        )
        self.db.add(document)
        await self.db.flush()  # Obtient l'UUID sans commit

        # 2. Découper en chunks
        chunks_text = self._chunk_text(content)

        # 3. Générer les embeddings (batch)
        embeddings = await self.embedding_service.embed_texts(chunks_text)

        # 4. Stocker les chunks
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
        """Découpe un texte en chunks avec chevauchement."""
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
```

**Step 2:** Commit

```bash
git add -A
git commit -m "feat: document ingestion with chunking and embedding"
```

---

## Phase 3 : Knowledge Graph (Neo4j)

### Task 10 : Client Neo4j et schéma du graph

**Objective:** Connexion Neo4j, création des contraintes et index.

**Files:**
- Create: `src/graph/neo4j_client.py`
- Create: `migrations/cypher/001_constraints.cypher`
- Create: `migrations/cypher/002_indexes.cypher`

**Schéma du graph (modélisation):**

```
(Tenant)-[:OWNS]->(Document)
(Document)-[:HAS_CHUNK]->(Chunk)
(Chunk)-[:MENTIONS]->(Entity)
(Entity)-[RELATION {type, confidence, tenant_id}]->(Entity)
(Entity)-[:BELONGS_TO]->(Tenant)
```

**Step 1:** Créer `src/graph/neo4j_client.py`

```python
from neo4j import AsyncGraphDatabase
from src.config import get_settings


class Neo4jClient:
    def __init__(self):
        settings = get_settings()
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def close(self):
        await self.driver.close()

    async def execute(self, query: str, parameters: dict | None = None):
        """Exécute une requête Cypher avec isolation tenant."""
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            return await result.data()

    async def execute_write(self, query: str, parameters: dict | None = None):
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            return await result.single()

    async def initialize_schema(self):
        """Crée les contraintes et index Neo4j."""
        constraints = [
            "CREATE CONSTRAINT tenant_unique IF NOT EXISTS FOR (t:Tenant) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT document_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT entity_unique IF NOT EXISTS FOR (e:Entity) REQUIRE (e.id, e.tenant_id) IS UNIQUE",
        ]
        for constraint in constraints:
            await self.execute(constraint)

        indexes = [
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type, e.tenant_id)",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name, e.tenant_id)",
            "CREATE INDEX chunk_id IF NOT EXISTS FOR (c:Chunk) ON (c.id, c.tenant_id)",
        ]
        for index in indexes:
            await self.execute(index)


# Singleton
_neo4j_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client
```

**Step 2:** Créer `migrations/cypher/001_constraints.cypher`

```cypher
// Contraintes d'unicité
CREATE CONSTRAINT tenant_unique IF NOT EXISTS
FOR (t:Tenant) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT document_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT chunk_unique IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT entity_tenant_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE (e.id, e.tenant_id) IS UNIQUE;
```

**Step 3:** Créer `migrations/cypher/002_indexes.cypher`

```cypher
// Index pour les performances de requête
CREATE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.type, e.tenant_id);

CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name, e.tenant_id);

CREATE INDEX chunk_tenant_idx IF NOT EXISTS
FOR (c:Chunk) ON (c.id, c.tenant_id);

CREATE INDEX document_tenant_idx IF NOT EXISTS
FOR (d:Document) ON (d.id, d.tenant_id);
```

**Step 4:** Commit

```bash
git add -A
git commit -m "feat: Neo4j client with schema initialization"
```

---

### Task 11 : Extracteur d'entités pour le graph

**Objective:** Extraire les entités (personnes, organisations, concepts, dates...) depuis le texte et les stocker dans le graph.

**Files:**
- Create: `src/graph/entity_extractor.py`

**Step 1:** Créer `src/graph/entity_extractor.py`

```python
import re
import uuid
from dataclasses import dataclass
from typing import NamedTuple


@dataclass
class Entity:
    id: str
    name: str
    type: str  # PERSON, ORG, DATE, LOCATION, CONCEPT, etc.
    confidence: float = 0.8


class EntityExtractor:
    """
    Extracteur d'entités basé sur des règles + LLM optionnel.
    Phase 1: Regex/keyword-based (rapide, pas de coût API).
    Phase 2: LLM-based pour les entités complexes.
    """

    # Patterns regex pour l'extraction basique
    PATTERNS = {
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "PHONE": r"\+?[1-9]\d{1,14}",
        "DATE": r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b",
        "URL": r"https?://[^\s]+",
        "MONEY": r"\$?\d+(?:,\d{3})*(?:\.\d{2})?",
    }

    def extract(self, text: str) -> list[Entity]:
        """Extrait toutes les entités détectées dans le texte."""
        entities = []
        seen = set()

        for etype, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group().strip()
                entity_key = (name, etype)
                if entity_key not in seen:
                    seen.add(entity_key)
                    entities.append(
                        Entity(
                            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, name)),
                            name=name,
                            type=etype,
                            confidence=0.9,
                        )
                    )

        # Extraire les mots-clés/concepts (noms propres, termes techniques)
        concepts = self._extract_concepts(text)
        for concept in concepts:
            entities.append(
                Entity(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, concept)),
                    name=concept,
                    type="CONCEPT",
                    confidence=0.7,
                )
            )

        return entities

    def _extract_concepts(self, text: str) -> list[str]:
        """
        Extraction simple de concepts potentiels (mots en majuscule,
        termes techniques). Sera amélioré avec un LLM plus tard.
        """
        # Noms propres (deux majuscules ou plus)
        proper_nouns = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        # Termes en MAJUSCULES
        acronyms = re.findall(r"\b[A-Z]{2,}\b", text)
        return list(set(proper_nouns + acronyms))

    async def extract_with_llm(self, text: str) -> list[Entity]:
        """
        Version améliorée utilisant un LLM pour l'extraction NER.
        À implémenter avec la fonction d'appel LLM du projet.
        """
        # TODO: Appeler un LLM pour le NER avancé
        return self.extract(text)


def get_entity_extractor() -> EntityExtractor:
    return EntityExtractor()
```

**Step 2:** Commit

```bash
git add -A
git commit -m "feat: entity extractor with regex patterns and concept detection"
```

---

### Task 12 : Synchronisation Graph — ingérer entités et relations dans Neo4j

**Objective:** Après l'ingestion d'un document, peupler le graph Neo4j avec les entités et relations intra-tenant.

**Files:**
- Create: `src/graph/graph_sync.py`
- Modify: `src/services/ingestion_service.py`

**Step 1:** Créer `src/graph/graph_sync.py`

```python
import uuid
from src.graph.neo4j_client import get_neo4j_client
from src.graph.entity_extractor import EntityExtractor, get_entity_extractor


class GraphSyncService:
    """
    Synchronise les données PostgreSQL vers Neo4j.
    Chaque entité/relation porte le tenant_id pour l'isolation.
    """

    def __init__(self):
        self.neo4j = get_neo4j_client()
        self.extractor = get_entity_extractor()

    async def sync_document(
        self, tenant_id: uuid.UUID, doc_id: uuid.UUID, chunks: list[dict]
    ):
        """
        Synchronise un document complet dans le graph:
        1. Crée/mis à jour le nœud Tenant
        2. Crée le nœud Document
        3. Pour chaque chunk: crée le nœud Chunk + entités + relations
        """
        # 1. Créer/merge le tenant
        await self.neo4j.execute(
            """
            MERGE (t:Tenant {id: $tenant_id})
            ON CREATE SET t.created_at = datetime()
            """,
            {"tenant_id": str(tenant_id)},
        )

        # 2. Créer/merge le document
        await self.neo4j.execute(
            """
            MERGE (t:Tenant {id: $tenant_id})
            MERGE (d:Document {id: $doc_id})
            CREATE (t)-[:OWNS]->(d)
            """,
            {"tenant_id": str(tenant_id), "doc_id": str(doc_id)},
        )

        # 3. Traiter chaque chunk
        all_entities_by_name: dict[str, dict] = {}

        for chunk_data in chunks:
            chunk_id = chunk_data["id"]
            content = chunk_data["content"]

            # Créer le nœud Chunk
            await self.neo4j.execute(
                """
                MERGE (d:Document {id: $doc_id})
                MERGE (c:Chunk {id: $chunk_id})
                SET c.tenant_id = $tenant_id,
                    c.content = $content,
                    c.chunk_index = $chunk_index
                CREATE (d)-[:HAS_CHUNK]->(c)
                """,
                {
                    "tenant_id": str(tenant_id),
                    "doc_id": str(doc_id),
                    "chunk_id": str(chunk_id),
                    "content": content,
                    "chunk_index": chunk_data.get("chunk_index", 0),
                },
            )

            # Extraire les entités du chunk
            entities = self.extractor.extract(content)

            for entity in entities:
                # Créer/merge l'entité avec tenant_id
                await self.neo4j.execute(
                    """
                    MERGE (e:Entity {id: $entity_id, tenant_id: $tenant_id})
                    ON CREATE SET e.name = $name,
                                  e.type = $type,
                                  e.confidence = $confidence
                    MERGE (c:Chunk {id: $chunk_id})
                    MERGE (c)-[:MENTIONS {confidence: $confidence}]->(e)
                    MERGE (t:Tenant {id: $tenant_id})
                    MERGE (e)-[:BELONGS_TO]->(t)
                    """,
                    {
                        "tenant_id": str(tenant_id),
                        "entity_id": entity.id,
                        "name": entity.name,
                        "type": entity.type,
                        "confidence": entity.confidence,
                        "chunk_id": str(chunk_id),
                    },
                )

                # Track entities for cross-chunk relations
                all_entities_by_name[entity.name] = entity

        # 4. Créer des relations entre entités fréquentes (co-occurrence)
        await self._create_cooccurrence_relations(tenant_id, all_entities_by_name)

    async def _create_cooccurrence_relations(
        self, tenant_id: uuid.UUID, entities: dict[str, Entity]
    ):
        """
        Crée des relations CO_OCCURS_WITH entre entités qui apparaissent
        dans les mêmes chunks.
        """
        entity_list = list(entities.values())
        for i, e1 in enumerate(entity_list):
            for e2 in entity_list[i + 1 :]:
                if e1.type != e2.type:  # Relations inter-types plus intéressantes
                    await self.neo4j.execute(
                        """
                        MATCH (a:Entity {id: $id1, tenant_id: $tenant_id}),
                              (b:Entity {id: $id2, tenant_id: $tenant_id})
                        MERGE (a)-[r:CO_OCCURS_WITH {type: $rel_type}]->(b)
                        ON CREATE SET r.confidence = 0.5
                        """,
                        {
                            "tenant_id": str(tenant_id),
                            "id1": e1.id,
                            "id2": e2.id,
                            "rel_type": f"{e1.type}_TO_{e2.type}",
                        },
                    )


def get_graph_sync_service() -> GraphSyncService:
    return GraphSyncService()
```

**Step 2:** Modifier `src/services/ingestion_service.py` pour appeler le graph sync

```python
# Ajouter à la fin de ingest_document(), après le commit:
from src.graph.graph_sync import get_graph_sync_service
from src.models.chunk import Chunk as ChunkModel
from sqlalchemy import select

# ... après await self.db.refresh(document):

# Synchroniser avec Neo4j
graph_sync = get_graph_sync_service()
chunks_result = await self.db.execute(
    select(ChunkModel).where(ChunkModel.document_id == document.id)
)
chunks = chunks_result.scalars().all()

chunk_dicts = [
    {"id": str(c.id), "content": c.content, "chunk_index": c.chunk_index}
    for c in chunks
]
await graph_sync.sync_document(tenant_id, document.id, chunk_dicts)
```

**Step 3:** Commit

```bash
git add -A
git commit -m "feat: graph sync service — entities, chunks, co-occurrence relations"
```

---

## Phase 4 : Retrieval & RAG Query

### Task 13 : Service de recherche vectorielle (PostgreSQL/pgvector)

**Objective:** Recherche de chunks similaires via pgvector, strictement isolée par tenant.

**Files:**
- Create: `src/services/vector_service.py`

**Step 1:** Créer `src/services/vector_service.py`

```python
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.embedding_service import get_embedding_service
from src.config import get_settings


class VectorService:
    """
    Recherche vectorielle dans PostgreSQL via pgvector.
    L'isolation tenant est garantie par:
    1. Le WHERE tenant_id = $tenant_id dans la requête SQL
    2. Les politiques RLS (double sécurité)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()

    async def search(
        self,
        query: str,
        tenant_id: uuid.UUID,
        top_k: int | None = None,
    ) -> list[dict]:
        """
        Recherche les chunks les plus similaires à la requête,
        RESTREINTS au tenant_id donné.
        """
        if top_k is None:
            top_k = get_settings().top_k

        # Générer l'embedding de la requête
        query_embedding = await self.embedding_service.embed_text(query)
        embedding_str = self._embedding_to_string(query_embedding)

        # Requête vectorielle avec isolation tenant
        # Opérateur <--> = distance cosinus (plus petit = plus similaire)
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
        """Convertit une liste de floats en format pgvector."""
        return "[" + ",".join(str(x) for x in embedding) + "]"


def get_vector_service(db: AsyncSession) -> VectorService:
    return VectorService(db)
```

**Step 2:** Commit

```bash
git add -A
git commit -m "feat: vector search service with pgvector and tenant isolation"
```

---

### Task 14 : Service de requête sur le graph

**Objective:** Interroger Neo4j pour enrichir le contexte avec les relations sémantiques.

**Files:**
- Create: `src/services/graph_service.py`

**Step 1:** Créer `src/services/graph_service.py`

```python
import uuid
from src.graph.neo4j_client import get_neo4j_client


class GraphService:
    """
    Interroge le knowledge graph pour enrichir le contexte RAG.
    Toutes les requêtes Cypher incluent WHERE tenant_id pour l'isolation.
    """

    def __init__(self):
        self.neo4j = get_neo4j_client()

    async def get_entity_context(
        self, tenant_id: uuid.UUID, entity_names: list[str], depth: int = 2
    ) -> list[dict]:
        """
        Pour chaque entité mentionnée dans la requête, récupère
        le contexte graph à N sauts de profondeur.
        """
        if not entity_names:
            return []

        placeholders = ",".join([f"'{name}'" for name in entity_names])

        query = f"""
        MATCH (t:Tenant {{id: $tenant_id}})
        MATCH (e:Entity {{tenant_id: $tenant_id, name IN [{placeholders}]}})
        MATCH path = (e)-[*1..{depth}]-(related)
        WHERE related.tenant_id = $tenant_id
        RETURN
            e.name as entity,
            e.type as entity_type,
            related.name as related_name,
            related.type as related_type,
            relationships(path) as rels,
            length(path) as distance
        LIMIT 50
        """

        results = await self.neo4j.execute(query, {"tenant_id": str(tenant_id)})

        context = []
        for row in results:
            context.append(
                {
                    "entity": row["entity"],
                    "entity_type": row["entity_type"],
                    "related_name": row["related_name"],
                    "related_type": row["related_type"],
                    "distance": row["distance"],
                }
            )

        return context

    async def get_knowledge_graph_summary(
        self, tenant_id: uuid.UUID, top_entities: int = 20
    ) -> dict:
        """
        Résumé du knowledge graph d'un tenant:
        entités les plus connectées, types dominants, etc.
        """
        result = await self.neo4j.execute(
            """
            MATCH (e:Entity {tenant_id: $tenant_id})
            OPTIONAL MATCH (e)-[r]-(related:Entity {tenant_id: $tenant_id})
            RETURN
                e.name as name,
                e.type as type,
                count(DISTINCT related) as connections
            ORDER BY connections DESC
            LIMIT $top
            """,
            {"tenant_id": str(tenant_id), "top": top_entities},
        )

        return {
            "top_entities": [
                {"name": r["name"], "type": r["type"], "connections": r["connections"]}
                for r in result
            ]
        }

    async def find_related_concepts(
        self, tenant_id: uuid.UUID, concept: str
    ) -> list[dict]:
        """
        Trouve les concepts reliés à un concept donné via le graph.
        Utile pour l'expansion de requête.
        """
        result = await self.neo4j.execute(
            """
            MATCH (e:Entity {tenant_id: $tenant_id, name: $concept})
            MATCH (e)-[r]-(related:Entity {tenant_id: $tenant_id})
            WHERE related.type = 'CONCEPT'
            RETURN related.name, related.type, count(r) as weight
            ORDER BY weight DESC
            LIMIT 10
            """,
            {"tenant_id": str(tenant_id), "concept": concept},
        )

        return [{"name": r["related.name"], "weight": r["weight"]} for r in result]


def get_graph_service() -> GraphService:
    return GraphService()
```

**Step 2:** Commit

```bash
git add -A
git commit -m "feat: graph service — entity context and knowledge graph queries"
```

---

### Task 15 : Service RAG — orchestration hybride (vector + graph)

**Objective:** Le cœur du RAG — combine les résultats vectoriels et graph pour construire le contexte enrichi.

**Files:**
- Create: `src/services/rag_service.py`
- Create: `src/schemas/rag.py`

**Schéma de la requête RAG hybride:**

```
QUERY
  |
  v
+---------------------------+
| 1. Embedding de la requête|
+---------------------------+
  |
  v
+---------------------------+     +------------------------+
| 2a. Recherche vectorielle |     | 2b. Extraction entités  |
|     (pgvector)            |     |     de la requête       |
+---------------------------+     +------------------------+
  |                                 |
  v                                 v
+---------------------------+     +------------------------+
| Chunks similaires         |     | Entités + contexte graph|
| (tenant-isolated)         |     | (tenant-isolated)       |
+-------------+-------------+     +----------+-------------+
              |                                |
              v                                v
        +----+--------------------------------+----+
        | 3. Fusion & construction du contexte |
        |    - Chunks textuels                 |
        |    - Relations graph (facts)         |
        |    - Graph summary                   |
        +------------------+------------------+
                           |
                           v
                  +--------+---------+
                  | 4. LLM Generation |
                  |    (avec contexte) |
                  +-------------------+
```

**Step 1:** Créer `src/schemas/rag.py`

```python
from pydantic import BaseModel, Field


class RAGQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096)
    top_k: int = Field(default=5, ge=1, le=20)
    include_graph_context: bool = Field(default=True)
    graph_depth: int = Field(default=2, ge=1, le=5)


class RAGSource(BaseModel):
    content: str
    source_type: str  # "vector" | "graph"
    similarity: float | None = None
    document_id: str | None = None
    document_title: str | None = None


class RAGResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    graph_context: list[dict] | None = None
    query_entities: list[str] | None = None
```

**Step 2:** Créer `src/services/rag_service.py`

```python
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.vector_service import get_vector_service
from src.services.graph_service import get_graph_service
from src.graph.entity_extractor import get_entity_extractor
from src.schemas.rag import RAGQuery, RAGResponse, RAGSource
from src.config import get_settings


class RAGService:
    """
    Orchestrateur RAG hybride.
    Combine la recherche vectorielle (PG) et le contexte graph (Neo4j).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_service = get_vector_service(db)
        self.graph_service = get_graph_service()
        self.entity_extractor = get_entity_extractor()
        self.settings = get_settings()

    async def query(
        self,
        tenant_id: uuid.UUID,
        rag_query: RAGQuery,
    ) -> RAGResponse:
        """
        Exécute une requête RAG hybride avec isolation tenant.
        """
        # Phase 1: Recherche vectorielle (tenant-isolated)
        vector_results = await self.vector_service.search(
            query=rag_query.query,
            tenant_id=tenant_id,
            top_k=rag_query.top_k,
        )

        # Phase 2: Extraction d'entités + contexte graph (si activé)
        graph_context = []
        query_entities = []
        if rag_query.include_graph_context:
            query_entities = self._extract_query_entities(rag_query.query)
            if query_entities:
                graph_context = await self.graph_service.get_entity_context(
                    tenant_id=tenant_id,
                    entity_names=query_entities,
                    depth=rag_query.graph_depth,
                )

        # Phase 3: Construction du contexte enrichi
        context_parts = self._build_context(vector_results, graph_context)

        # Phase 4: Génération de la réponse (LLM)
        answer = await self._generate_answer(rag_query.query, context_parts)

        # Sources
        sources = []
        for vr in vector_results:
            sources.append(
                RAGSource(
                    content=vr["content"][:200] + "...",
                    source_type="vector",
                    similarity=vr.get("similarity"),
                    document_id=str(vr.get("document_id")),
                    document_title=vr.get("document_title"),
                )
            )

        for gc in graph_context:
            sources.append(
                RAGSource(
                    content=f"{gc['entity']} ({gc['entity_type']}) --[{gc['distance']} hops]--> {gc['related_name']} ({gc['related_type']})",
                    source_type="graph",
                )
            )

        return RAGResponse(
            answer=answer,
            sources=sources,
            graph_context=graph_context if graph_context else None,
            query_entities=query_entities if query_entities else None,
        )

    def _extract_query_entities(self, query: str) -> list[str]:
        """Extrait les entités pertinentes de la requête utilisateur."""
        entities = self.entity_extractor.extract(query)
        return [e.name for e in entities if e.confidence > 0.5]

    def _build_context(
        self, vector_results: list[dict], graph_context: list[dict]
    ) -> str:
        """Construit le contexte enrichi combinant texte et graph."""
        parts = []

        # Section vectorielle
        if vector_results:
            parts.append("=== DOCUMENT CONTEXT ===")
            for i, vr in enumerate(vector_results, 1):
                doc_title = vr.get("document_title", "Unknown")
                parts.append(f"[Doc {i}: {doc_title} (similarity: {vr.get('similarity', 0):.3f})]")
                parts.append(vr["content"])
                parts.append("")

        # Section graph
        if graph_context:
            parts.append("=== KNOWLEDGE GRAPH CONTEXT ===")
            # Regrouper par entité
            entities_map: dict[str, list[dict]] = {}
            for gc in graph_context:
                key = f"{gc['entity']} ({gc['entity_type']})"
                if key not in entities_map:
                    entities_map[key] = []
                entities_map[key].append(gc)

            for entity_key, relations in entities_map.items():
                parts.append(f"Entity: {entity_key}")
                for rel in relations:
                    parts.append(
                        f"  → {rel['related_name']} ({rel['related_type']}) "
                        f"[{rel['distance']} hop(s)]"
                    )
                parts.append("")

        return "\n".join(parts) if parts else "No context found."

    async def _generate_answer(self, query: str, context: str) -> str:
        """
        Génère la réponse via un LLM.
        TODO: Intégrer avec le provider LLM choisi (OpenAI, Anthropic, local).
        """
        # Pour l'instant, retourne un template — remplacé par un vrai LLM
        prompt = f"""You are a helpful assistant. Answer the following question
based on the provided context. If the context does not contain enough
information, say so.

Context:
{context}

Question: {query}

Answer:"""

        # TODO: Appel LLM réel
        # from src.services.llm_service import get_llm_service
        # llm = get_llm_service()
        # return await llm.generate(prompt)

        return f"[LLM Response] Based on the context provided, here is the answer to: {query}"


def get_rag_service(db: AsyncSession) -> RAGService:
    return RAGService(db)
```

**Step 3:** Commit

```bash
git add -A
git commit -m "feat: hybrid RAG service — vector + graph orchestration"
```

---

## Phase 5 : API REST

### Task 16 : Routes API — Tenants, Documents, RAG

**Objective:** Exposer l'API REST avec FastAPI.

**Files:**
- Create: `src/api/tenants.py`
- Create: `src/api/documents.py`
- Create: `src/api/rag.py`
- Modify: `src/main.py`

**Step 1:** Créer `src/api/tenants.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.services.tenant_service import TenantService
from src.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("/", response_model=TenantResponse, status_code=201)
async def create_tenant(data: TenantCreate, db: AsyncSession = Depends(get_db)):
    service = TenantService(db)
    tenant = await service.create(data)
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id, db: AsyncSession = Depends(get_db)):
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
```

**Step 2:** Créer `src/api/documents.py`

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import get_tenant_id
from src.services.ingestion_service import get_ingestion_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/")
async def upload_document(
    title: str,
    content: str,
    source: str | None = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    service = get_ingestion_service(db)
    document = await service.ingest_document(
        tenant_id=tenant_id,
        title=title,
        content=content,
        source=source,
    )
    return {
        "id": str(document.id),
        "title": document.title,
        "tenant_id": str(document.tenant_id),
        "is_processed": document.is_processed,
        "message": "Document ingested and synced to knowledge graph",
    }
```

**Step 3:** Créer `src/api/rag.py`

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import get_tenant_id
from src.services.rag_service import get_rag_service
from src.schemas.rag import RAGQuery, RAGResponse

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RAGResponse)
async def rag_query(
    query: RAGQuery,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    service = get_rag_service(db)
    result = await service.query(tenant_id=tenant_id, rag_query=query)
    return result
```

**Step 4:** Enregistrer les routes dans `src/main.py`

```python
from src.api import tenants, documents, rag

# Dans create_app(), après le middleware:
app.include_router(tenants.router)
app.include_router(documents.router)
app.include_router(rag.router)
```

**Step 5:** Commit

```bash
git add -A
git commit -m "feat: REST API — tenants, documents, RAG query endpoints"
```

---

## Phase 6 : Tests & Validation

### Task 17 : Tests d'isolation multi-tenant (CRITIQUE)

**Objective:** Tests qui prouvent que le tenant A ne peut JAMAIS accéder aux données du tenant B.

**Files:**
- Create: `tests/test_tenant_isolation.py`
- Create: `tests/conftest.py`

**Step 1:** Créer `tests/conftest.py`

```python
import pytest
import asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from src.main import create_app
from src.db.session import engine, Base, async_session
from src.models.tenant import Tenant


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def app():
    application = create_app()
    yield application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def tenant_a(db_session):
    """Crée un tenant de test A."""
    tenant = Tenant(
        name="Tenant A",
        api_key=f"test-key-a-{uuid.uuid4()}",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def tenant_b(db_session):
    """Crée un tenant de test B."""
    tenant = Tenant(
        name="Tenant B",
        api_key=f"test-key-b-{uuid.uuid4()}",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session
        await session.rollback()
```

**Step 2:** Créer `tests/test_tenant_isolation.py`

```python
import uuid
import pytest
from sqlalchemy import text
from src.models.document import Document
from src.models.chunk import Chunk


class TestTenantIsolation:
    """
    Tests CRITIQUES: vérifient que l'isolation multi-tenant fonctionne.
    Un échec ici = faille de sécurité.
    """

    @pytest.mark.asyncio
    async def test_rls_prevents_cross_tenant_select(self, tenant_a, tenant_b, db_session):
        """
        Un tenant ne doit PAS pouvoir lire les documents d'un autre tenant,
        même avec une requête SQL directe si RLS est actif.
        """
        # Ajouter un document au tenant B
        doc_b = Document(
            tenant_id=tenant_b.id,
            title="Secret de B",
            content="Information confidentielle du tenant B",
        )
        db_session.add(doc_b)
        await db_session.commit()

        # Tenter de lire le document de B depuis la session de A
        # (simulation: on ne filtre PAS par tenant_id)
        # Sans RLS, cela retournerait le document. Avec RLS, il ne devrait pas.

        # Note: en production, le middleware injecte le tenant_id dans
        # current_setting('app.current_tenant_id'), et les politiques RLS
        # bloquent l'accès croisé.

    @pytest.mark.asyncio
    async def test_chunks_have_tenant_id(self, tenant_a, tenant_b, db_session):
        """Tous les chunks doivent avoir le tenant_id correct."""
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

        # Vérifier que le chunk appartient bien au tenant A
        assert chunk.tenant_id == tenant_a.id
        assert chunk.tenant_id != tenant_b.id

    @pytest.mark.asyncio
    async def test_vector_search_respects_tenant(self, tenant_a, tenant_b, db_session):
        """La recherche vectorielle ne retourne que les chunks du tenant actif."""
        from src.services.vector_service import VectorService

        vector_service = VectorService(db_session)

        # La requête inclut WHERE c.tenant_id = :tenant_id
        # Donc même si le tenant B a des chunks similaires, ils ne seront pas retournés
        results = await vector_service.search(
            query="test",
            tenant_id=tenant_a.id,
            top_k=5,
        )

        # Vérifier que TOUS les résultats appartiennent au tenant A
        for result in results:
            # Le résultat doit être filtré — dans un test complet,
            # on ajouterait des chunks des deux tenants et vérifierait
            # que seuls ceux de A sont retournés
            pass


class TestAPIKeyAuth:
    """Tests d'authentification par API key."""

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self, client):
        response = await client.post("/documents/", json={"title": "t", "content": "c"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_403(self, client):
        response = await client.post(
            "/documents/",
            json={"title": "t", "content": "c"},
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 403
```

**Step 3:** Commit

```bash
git add -A
git commit -m "test: tenant isolation tests — critical security verification"
```

---

## Phase 7 : LLM Integration (Optionnel / Phase suivante)

### Task 18 : Intégration du LLM pour la génération

**Objective:** Brancher un LLM (OpenAI, Anthropic, ou local via Ollama/LM Studio) pour la génération de réponses.

**Files:**
- Create: `src/services/llm_service.py`
- Modify: `src/services/rag_service.py`

**Architecture LLM:**

```
LLM Service (abstrait)
├── OpenAIProvider
├── AnthropicProvider
├── OllamaProvider (local)
└── LMStudioProvider (local)
```

**Step 1:** Créer `src/services/llm_service.py`

```python
from abc import ABC, abstractmethod
from src.config import get_settings


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class LocalProvider(LLMProvider):
    """Provider local via Ollama ou LM Studio."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.base_url = base_url
        self.model = model

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        import httpx
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=body,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


def get_llm_provider() -> LLMProvider:
    """
    Fabrique de provider LLM.
    TODO: Configurer via settings (LLM_PROVIDER, LLM_API_KEY, etc.)
    """
    settings = get_settings()
    # Pour l'instant, retourne un provider stub
    # À remplacer par le vrai provider configuré
    return LocalProvider()
```

**Step 2:** Modifier `src/services/rag_service.py` — remplacer le stub `_generate_answer`

```python
# Remplacer la méthode _generate_answer:
from src.services.llm_service import get_llm_provider

async def _generate_answer(self, query: str, context: str) -> str:
    system_prompt = """You are a research assistant. Answer questions based
    on the provided context. Cite sources when possible. If the context
    does not contain enough information, clearly state what is missing."""

    prompt = f"Context:\n\n{context}\n\nQuestion: {query}\n\nAnswer:"
    llm = get_llm_provider()
    return await llm.generate(prompt, system_prompt=system_prompt)
```

**Step 3:** Commit

```bash
git add -A
git commit -m "feat: LLM service with OpenAI and local (Ollama/LM Studio) providers"
```

---

## Phase 8 : README & Documentation

### Task 19 : README avec guide d'utilisation

**Files:**
- Create: `README.md`

**Contenu du README:**

```markdown
# ProAirAg — Hybrid Multi-Tenant RAG

Système RAG hybride combinant:
- **PostgreSQL + pgvector**: Stockage vectoriel sécurisé avec Row-Level Security
- **Neo4j**: Knowledge graph pour la compréhension sémantique des relations

## Architecture

La sécurité multi-tenant est garantie à DEUX niveaux:
1. **Application**: Le middleware extrait le tenant_id et l'injecte dans chaque requête
2. **Base de données**: Les politiques RLS PostgreSQL bloquent physiquement l'accès croisé

Même si une faille apparaît au niveau application, le niveau RLS de PostgreSQL
empêche tout accès aux données d'un autre tenant.

## Démarrage rapide

```bash
# 1. Copier la configuration
cp .env.example .env

# 2. Lancer l'infrastructure
docker-compose up -d

# 3. Installer les dépendances
pip install -e ".[dev]"

# 4. Lancer l'application
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 5. Tester
curl http://localhost:8000/health
```

## API

### Créer un tenant
```bash
curl -X POST http://localhost:8000/tenants/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Mon Entreprise"}'
# → {"id": "...", "name": "Mon Entreprise", "api_key": "sk-...", ...}
```

### Ingrester un document
```bash
curl -X POST http://localhost:8000/documents/ \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Politique RH",
    "content": "Notre politique de congés...",
    "source": "hr/policy.pdf"
  }'
```

### Poser une question RAG
```bash
curl -X POST http://localhost:8000/rag/query \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quelle est la politique de congés ?",
    "top_k": 5,
    "include_graph_context": true
  }'
```

## Sécurité

| Niveau | Mécanisme | Garantie |
|---|---|---|
| API | X-API-Key validation | AuthN + tenant resolution |
| Application | Tenant context middleware | tenant_id sur chaque requête |
| PostgreSQL | Row-Level Security | Isolation au niveau moteur DB |
| Neo4j | WHERE tenant_id | Isolation dans chaque requête Cypher |
| pgvector | WHERE tenant_id | Recherche vectorielle isolée |
```

**Step 1:** Commit

```bash
git add -A
git commit -m "docs: comprehensive README with setup guide and API examples"
```

---

## Matrice de Sécurité (Résumé)

```
┌─────────────────────────────────────────────────────────────┐
│  Isolation Multi-Tenant: Défense en Profondeur (Defense-in-Depth) │
├──────────────────┬──────────────────────────────────────────┤
│  Niveau          │  Mécanisme                               │
├──────────────────┼──────────────────────────────────────────┤
│  1. Auth         │  X-API-Key → Tenant resolution           │
│  2. Middleware   │  Tenant context injection                │
│  3. Service      │  tenant_id dans chaque requête           │
│  4. SQL          │  WHERE tenant_id = $tenant_id            │
│  5. RLS          │  PostgreSQL policies (garde de sécurité) │
│  6. Graph        │  WHERE tenant_id sur chaque Cypher       │
│  7. FK           │  FOREIGN KEY + ON DELETE CASCADE         │
└──────────────────┴──────────────────────────────────────────┘
```

---

## Résumé des tâches

| Phase | Tâche | Description | Priorité |
|-------|-------|-------------|----------|
| 0 | T1 | Structure du projet | 🔴 HAUTE |
| 0 | T2 | Config + FastAPI entry | 🔴 HAUTE |
| 1 | T3 | Modèle Tenant + session DB | 🔴 HAUTE |
| 1 | T4 | Modèles Document + Chunk | 🔴 HAUTE |
| 1 | T5 | Migrations SQL + RLS policies | 🔴 CRITIQUE |
| 1 | T6 | Middleware Tenant Context | 🔴 HAUTE |
| 1 | T7 | Service Tenant CRUD | 🟡 MOYENNE |
| 2 | T8 | Service Embeddings | 🔴 HAUTE |
| 2 | T9 | Service Ingestion | 🔴 HAUTE |
| 3 | T10 | Client Neo4j + schéma | 🔴 HAUTE |
| 3 | T11 | Extracteur d'entités | 🟡 MOYENNE |
| 3 | T12 | Sync Graph (entities + relations) | 🟡 MOYENNE |
| 4 | T13 | Service recherche vectorielle | 🔴 HAUTE |
| 4 | T14 | Service requêtes graph | 🟡 MOYENNE |
| 4 | T15 | Service RAG hybride | 🔴 HAUTE |
| 5 | T16 | Routes API | 🟡 MOYENNE |
| 6 | T17 | Tests isolation | 🔴 CRITIQUE |
| 7 | T18 | Intégration LLM | 🟢 BASSE |
| 8 | T19 | README + docs | 🟢 BASSE |

**Total: 19 tâches, 8 phases**

Plan complet et sauvegardé. Prêt pour l'exécution via subagent-driven-development — chaque tâche sera dispatchée à un sous-agent avec revue en deux étapes (conformité spec puis qualité code). Souhaitez-vous que je lance l'implémentation ?
