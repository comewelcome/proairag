# ProAiRag

Hybrid multi-tenant RAG (Retrieval-Augmented Generation) platform combining PostgreSQL vector search with Neo4j knowledge graph reasoning. Features department-level access control, a React dashboard SPA, and an MCP server for AI agent integration.

---

## Architecture

ProAiRag uses two complementary databases, each optimized for a specific role:

```
                  +------------------+
                  |   FastAPI API    |
                  | + React SPA      |
                  +--------+---------+
                           |
              +------------+------------+
              |                         |
      +-------v-------+         +-------v-------+
      |  PostgreSQL   |         |     Neo4j     |
      |  (pgvector)   |         |  (Graph DB)   |
      +---------------+         +---------------+
```

### PostgreSQL — Source of truth for all relational data

PostgreSQL handles everything that requires ACID transactions, structured queries, and row-level security:

| Table | Purpose |
|-------|---------|
| `tenants` | Multi-tenant isolation with RLS policies |
| `departments` | Organizational hierarchy per tenant |
| `users` + `user_departments` | Authentication + role-based access control |
| `documents` | Full text content + metadata + department scoping |
| `chunks` | Text fragments + 384-dim embeddings (pgvector HNSW index) |
| `conversations` + `messages` | Chat history with RAG sources (JSONB) |
| `tenant_settings` | Per-tenant RAG configuration (chunk size, LLM provider, top_k) |

Key PostgreSQL features used:
- **pgvector** with HNSW index for fast cosine-similarity vector search
- **Row-Level Security (RLS)** policies on all tenant-scoped tables (defense-in-depth)
- **JSONB** for flexible storage of RAG sources and graph context in chat messages
- **Composite indexes** on frequent query paths: `chunks(tenant_id, document_id)`, `messages(conversation_id, created_at DESC)`
- **Cascade deletes** via foreign keys for referential integrity

### Neo4j — Semantic reasoning engine

Neo4j stores ONLY entity nodes and their relationships — no content duplication with PostgreSQL. It is used exclusively for graph-based context enrichment during RAG queries.

```
Chunk {id, tenant_id, document_id, department_id, chunk_index}
  |
  +--[:MENTIONS]--> Entity {id, tenant_id, name, type, confidence}
                      |
                      +--[:CO_OCCURS_WITH {type, count}]--> Entity
```

What Neo4j does:
- Stores extracted entities (EMAIL, PHONE, DATE, URL, MONEY, CONCEPT) from document text
- Tracks which chunks mention which entities via `MENTIONS` relationships
- Builds cross-type co-occurrence graph (`CO_OCCURS_WITH`) for semantic reasoning
- Powers entity context queries: "What entities are related to X?" with configurable traversal depth

What Neo4j does NOT store:
- No Tenant, Document, or Department nodes — those IDs are Chunk properties (references to PostgreSQL)
- No chunk content text — already in PostgreSQL
- No user/auth data — exclusively in PostgreSQL

### Database responsibility matrix

| Function | PostgreSQL | Neo4j |
|----------|:----------:|-------:|
| Tenant/Department/User CRUD | Primary | — |
| Document storage + full text | Primary | — |
| Vector embeddings + similarity search | Exclusive | — |
| Chat history + conversation state | Exclusive | — |
| Entity extraction results | — | Storage + relations |
| Entity relationship queries | — | Exclusive |
| Co-occurrence analysis | — | Exclusive |
| Row-level security (tenant isolation) | Exclusive | App-level WHERE tenant_id |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Python 3.11+ |
| ORM | async SQLAlchemy 2.0 (Mapped/mapped_column) |
| Vector DB | PostgreSQL + pgvector (HNSW index) |
| Graph DB | Neo4j 5 Community |
| Embeddings | sentence-transformers (paraphrase-MiniLM-L3-v2, 384-dim) |
| LLM | OpenAI-compatible API (llama.cpp Qwen3.6-27B default) |
| Auth | JWT (HS256) + API key dual authentication |
| Frontend | React 19 + TypeScript + Vite + TailwindCSS v4 |
| Dashboard Router | TanStack Router |
| MCP Server | FastMCP (10 tools) |
| Containerization | Docker Compose (postgres, neo4j, api, nginx) |
| Testing | pytest + pytest-asyncio + httpx |

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.11+ (for local development)

### 1. Clone and configure

```bash
git clone <repository-url>
cd proairag
cp .env.example .env
```

Edit `.env` with your credentials. Required variables:

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/proairag
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
SECRET_KEY=your-jwt-secret-key  # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Start with Docker Compose

```bash
docker compose up -d
```

This starts:
- **PostgreSQL 15** with pgvector extension (port 5432) — migrations run automatically on first start
- **Neo4j 5 Community** (ports 7474/7687) — constraints/indexes created at app startup
- **FastAPI** with hot reload (port 8000)
- **Nginx** reverse proxy (port 80)

### 3. Access the application

- Dashboard: http://localhost
- API docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

### Local development (no Docker)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install ".[dev,embedding]"

# Start PostgreSQL and Neo4j separately (Docker or native)

# Run the API
uvicorn src.main:app --reload --port 8000

# Run the frontend dev server
cd frontend && npm run dev
```

---

## Authentication

ProAiRag supports two authentication methods:

### JWT Authentication (user-level)

Used by the dashboard frontend. Provides department-level access control.

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Returns: { "access_token": "eyJ...", "token_type": "bearer" }
```

Use the token in subsequent requests:
```bash
curl http://localhost:8000/api/documents/ \
  -H "Authorization: Bearer <token>"
```

JWT claims include `user_id`, `tenant_id`, `is_tenant_admin`, and `is_super_admin`.

### API Key Authentication (tenant-level)

Used by programmatic integrations and the MCP server. Bypasses department filters.

```bash
curl http://localhost:8000/api/documents/ \
  -H "X-API-Key: sk-your-api-key"
```

---

## API Endpoints

All API routes are prefixed with `/api/`.

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents/` | List documents (tenant + department isolated) |
| POST | `/api/documents/` | Ingest document from JSON payload |
| POST | `/api/documents/upload` | Upload file (PDF/TXT/DOCX) with LiteParse |
| DELETE | `/api/documents/{doc_id}` | Delete document + chunks + Neo4j cleanup |

### RAG

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rag/query` | Hybrid RAG query (vector + graph + LLM) |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/sessions/` | Create new chat session |
| GET | `/api/chat/sessions/` | List chat sessions |
| GET | `/api/chat/sessions/{id}` | Get session with messages |
| POST | `/api/chat/sessions/{id}/send` | Send message, get RAG response |
| DELETE | `/api/chat/sessions/{id}` | Delete session |

### Departments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/departments/` | List departments |
| POST | `/api/departments/` | Create department |
| PUT | `/api/departments/{id}` | Update department |
| DELETE | `/api/departments/{id}` | Delete department |
| POST | `/api/departments/{id}/users` | Assign user to department |

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings/` | Get tenant RAG settings |
| PUT | `/api/settings/` | Update RAG settings |
| GET | `/api/settings/stats` | System stats (docs, chunks, entities, DB health) |

### Admin (super admin only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/tenants/` | List all tenants |
| DELETE | `/api/admin/tenants/{id}` | Deactivate tenant |
| GET | `/api/admin/tenants/{id}/users/` | List tenant users |
| POST | `/api/admin/tenants/{id}/users/` | Create user in tenant |
| PUT | `/api/admin/tenants/{id}/users/{uid}` | Update user |
| DELETE | `/api/admin/tenants/{id}/users/{uid}` | Delete user |

---

## RAG Pipeline

The hybrid RAG query pipeline combines vector search with knowledge graph context:

```
User Query
    |
    v
+------------------+     +-------------------+
|  Vector Search   |     | Entity Extraction |
|  (pgvector HNSW) |     |  (regex NER)      |
+--------+---------+     +--------+----------+
         |                        |
         v                        v
   Top-K chunks           Entity names
   with similarity                |
   scores                         v
                                 +------------------+
                                 |  Graph Traversal |
                                 |  (Neo4j, depth N)|
                                 +--------+---------+
                                          |
                                          v
   +-------------------------------------+
   |         Context Assembly            |
   |  Vector chunks + Graph entities     |
   +----------------+--------------------+
                    |
                    v
            +---------------+
            |    LLM        |
            |  (OpenAI or   |
            |   llama.cpp)  |
            +-------+-------+
                    |
                    v
           Answer + Sources
```

1. **Vector search**: Query is embedded, pgvector HNSW index retrieves top-K similar chunks
2. **Entity extraction**: Regex-based NER extracts entities (EMAIL, PHONE, DATE, URL, MONEY, CONCEPT) from the query
3. **Graph context**: Entities are looked up in Neo4j, and N-hop relationships are traversed
4. **Context assembly**: Vector results and graph relationships are combined into a prompt
5. **LLM generation**: The combined context is sent to the LLM with conversation history

---

## MCP Server

The MCP (Model Context Protocol) server exposes ProAiRag capabilities to AI agents (Claude Code, Cursor, etc.).

```bash
# Set environment variables
export DATABASE_URL="postgresql+asyncpg://..."
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-neo4j-password"
export API_KEY="sk-..."   # optional — or pass tenant_id directly

# Run the server
python src/mcp_server.py

# Or via FastMCP CLI
fastmcp run src/mcp_server.py:mcp
```

### Available tools

| Tool | Description |
|------|-------------|
| `health_check()` | Server status and connection info |
| `list_tenants()` | List all tenants |
| `create_tenant(name, ...)` | Create tenant with optional admin user |
| `list_documents(tenant_id?, ...)` | List tenant documents |
| `ingest_document(title, content, ...)` | Ingest document (chunking + embedding + graph sync) |
| `rag_query(query, tenant_id?, ...)` | Hybrid RAG query (vector + graph + LLM) |
| `graph_entity_context(entity_names, ...)` | Entity relationships in Neo4j |
| `graph_summary(tenant_id?, ...)` | Top connected entities |
| `find_related_concepts(concept, ...)` | Related CONCEPT entities |
| `list_departments(tenant_id?)` | List tenant departments |

See [MCP_SERVER.md](MCP_SERVER.md) for installation instructions and testing commands.

---

## Security

### Multi-tenant isolation

Three-layer defense-in-depth approach:

1. **Application level**: Every service method and API route scopes queries by `tenant_id`. Department-level filtering restricts non-admin users to their assigned departments.
2. **Database level (PostgreSQL)**: Row-Level Security (RLS) policies on `documents`, `chunks`, `conversations`, and `messages` tables enforce tenant isolation at the database engine level.
3. **Graph level (Neo4j)**: Every Cypher query includes `WHERE tenant_id = $tenant_id`. Entity nodes carry `tenant_id` as a property with a unique constraint.

### Authentication

- JWT tokens contain user identity and privilege claims (`is_tenant_admin`, `is_super_admin`)
- API keys provide tenant-level admin access (bypass department filters)
- Passwords are hashed with bcrypt
- Missing required secrets (database URL, Neo4j credentials, JWT secret) cause startup failure — no default passwords

---

## Project Structure

```
proairag/
├── src/
│   ├── main.py                  # FastAPI app factory + SPA serving
│   ├── config.py                # Pydantic settings (env var validation)
│   ├── db/
│   │   ├── session.py           # Async SQLAlchemy engine + session factory
│   │   └── seed.py              # Auto-seed super admin + dashboard tenants
│   ├── models/                  # SQLAlchemy ORM models (9 tables)
│   │   ├── tenant.py            # Tenant (multi-tenant root)
│   │   ├── department.py        # Department (org hierarchy)
│   │   ├── user.py              # User (auth + roles)
│   │   ├── user_department.py   # UserDepartment (junction table)
│   │   ├── document.py          # Document (full text + metadata)
│   │   ├── chunk.py             # Chunk (text + pgvector embedding)
│   │   ├── conversation.py      # Conversation (chat sessions)
│   │   ├── message.py           # Message (chat messages + RAG sources)
│   │   └── tenant_settings.py   # TenantSettings (per-tenant RAG config)
│   ├── schemas/                 # Pydantic v2 request/response models
│   ├── middleware/
│   │   └── tenant.py            # JWT + API key auth middleware
│   ├── services/                # Business logic layer
│   │   ├── auth_service.py      # Password hashing + JWT
│   │   ├── department_service.py# Department CRUD + user assignment
│   │   ├── embedding_service.py # Text embeddings (sentence-transformers)
│   │   ├── ingestion_service.py # Document ingestion + graph sync
│   │   ├── vector_service.py    # pgvector similarity search
│   │   ├── graph_service.py     # Neo4j entity context queries
│   │   ├── rag_service.py       # Hybrid RAG orchestration
│   │   ├── llm_service.py       # LLM provider interface
│   │   ├── chat_service.py      # Chat sessions + message sending
│   │   ├── tenant_service.py    # Tenant CRUD
│   │   └── settings_service.py  # RAG settings + system stats
│   ├── api/                     # FastAPI route definitions
│   │   ├── auth.py              # /api/auth/*
│   │   ├── documents.py         # /api/documents/*
│   │   ├── rag.py               # /api/rag/*
│   │   ├── chat.py              # /api/chat/*
│   │   ├── departments.py       # /api/departments/*
│   │   ├── tenants.py           # /api/tenants/*
│   │   ├── rag_settings.py      # /api/settings/*
│   │   └── admin.py             # /api/admin/*
│   ├── graph/                   # Neo4j integration
│   │   ├── neo4j_client.py      # Async driver + schema initialization
│   │   ├── entity_extractor.py  # Regex-based NER
│   │   └── graph_sync.py        # Document sync + cleanup
│   └── mcp_server.py            # MCP server (10 tools via FastMCP)
├── frontend/                    # React dashboard SPA
├── migrations/
│   ├── sql/                     # PostgreSQL migrations (12 files)
│   └── cypher/                  # Neo4j migrations (3 files)
├── tests/
│   ├── unit/                    # Unit tests (103 tests, mocks)
│   └── integration/             # Integration tests (38 tests, Docker)
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # API container
├── pyproject.toml               # Python dependencies
├── .env.example                 # Environment template
├── MCP_SERVER.md                # MCP server documentation
└── AGENTS.md                    # DOX framework
```

---

## Testing

```bash
# Unit tests (no database required)
pytest tests/unit/

# Integration tests (requires Docker: postgres + neo4j)
docker compose up -d postgres neo4j
pytest tests/integration/

# All tests
pytest
```

Test coverage includes tenant isolation, department isolation, authentication flows, entity extraction, schema validation, and full API flow.

---

## Configuration

All configuration comes from environment variables. See `.env.example` for the complete list.

| Variable | Required | Description |
|----------|:--------:|-------------|
| `DATABASE_URL` | Yes | PostgreSQL async connection string |
| `NEO4J_URI` | Yes | Neo4j bolt URI |
| `NEO4J_USER` | Yes | Neo4j username |
| `NEO4J_PASSWORD` | Yes | Neo4j password |
| `SECRET_KEY` | Yes | JWT signing secret |
| `EMBEDDING_MODEL` | No | Embedding model (default: paraphrase-MiniLM-L3-v2) |
| `EMBEDDING_DIMENSION` | No | Embedding dimension (default: 384) |
| `CHUNK_SIZE` | No | Words per chunk (default: 512) |
| `CHUNK_OVERLAP` | No | Chunk overlap in words (default: 64) |
| `TOP_K` | No | Vector search results (default: 5) |
| `LLM_PROVIDER` | No | LLM backend (default: openai) |
| `OPENAI_API_BASE` | No | LLM API endpoint |
| `OPENAI_MODEL` | No | LLM model name |
| `LLM_MAX_TOKENS` | No | Max LLM output tokens (default: 500) |
| `SUPER_ADMIN_EMAIL` | No | Auto-seeded super admin email |
| `SUPER_ADMIN_PASSWORD` | No | Auto-seeded super admin password |
| `DASHBOARD_LOGIN_N` | No | Auto-seeded demo tenant logins |

Per-tenant settings (chunk size, LLM provider, model, etc.) can be configured via the Settings page or `/api/settings/` endpoint and override the global defaults.

---

## License

Private
