# ProAiRag — Hybrid Multi-Tenant RAG System

ProAiRag is a production-grade Retrieval-Augmented Generation (RAG) platform combining
**PostgreSQL vector search (pgvector)** with **Neo4j knowledge graph reasoning**.

Built for enterprises requiring strict **multi-tenant isolation** and **department-level
access control**, with defense-in-depth security spanning application logic, database
Row-Level Security (RLS), and graph-level tenant scoping.

## Key Features

- **Hybrid RAG**: Vector similarity search (pgvector HNSW) + knowledge graph context
  (Neo4j entity relationships) fused into a single LLM prompt
- **Multi-tenant isolation**: Every tenant's data is physically separated at both
  application and database levels (PostgreSQL RLS policies)
- **Department-level access control**: Users see only documents in their assigned
  departments; tenant admins bypass department filtering
- **Dual authentication**: JWT tokens (user-level, department-scoped) and API keys
  (tenant-level, admin access)
- **Knowledge graph**: Automatic entity extraction (emails, phones, dates, URLs,
  money, concepts) with co-occurrence relationship mapping
- **MCP server**: 10 tools exposing RAG queries, document management, graph operations,
  and tenant management for AI assistant integrations (Claude, Cursor, etc.)
- **Embedding fallback**: Works with or without sentence-transformers (hash-based
  fallback for development)
- **Async throughout**: FastAPI + async SQLAlchemy + async Neo4j driver

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application                           │
├────────────┬────────────┬─────────────┬────────────┬───────────────────┤
│   Routes   │ Middleware │  Services   │   Models   │     Graph         │
│ (5 routers)│ (JWT/API)  │ (9 classes) │ (6 tables) │  (Neo4j + NER)    │
├────────────┴────────────┴─────────────┴────────────┴───────────────────┤
│                        Dual Authentication                             │
│  JWT Bearer Token (user + dept)  │  X-API-Key (tenant admin)           │
├───────────────────────────────────┼─────────────────────────────────────┤
│          PostgreSQL + pgvector    │           Neo4j                     │
│  ┌─────────────────────────────┐  │  ┌──────────────────────────────┐  │
│  │  RLS: tenant isolation      │  │  │  Tenant → owns → Document    │  │
│  │  HNSW: vector cosine search │  │  │  Document → has_chunk → Chunk│  │
│  │  FK: cascade delete rules   │  │  │  Chunk → mentions → Entity   │  │
│  └─────────────────────────────┘  │  │  Entity → CO_OCCURS_WITH →   │  │
│                                    │  │  Department → contains → Doc │  │
│                                    │  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Security — Defense in Depth

Security is enforced at **seven layers**. A failure at any single layer cannot
result in data leakage.

| Layer | Mechanism | Guarantee |
|-------|-----------|-----------|
| 1. API Gateway | `X-API-Key` or `Authorization: Bearer` | Authentication + tenant/user resolution |
| 2. Middleware | `TenantContextMiddleware` on every request | `tenant_id` + `user_id` injected into `request.state` |
| 3. Service Layer | `tenant_id` on every service method call | Application-level tenant isolation |
| 4. Department Filter | User departments resolved before queries | Users see only their departments (admin bypass) |
| 5. SQL Queries | `WHERE tenant_id = $tenant_id` on all queries | Explicit tenant scoping in raw SQL |
| 6. PostgreSQL RLS | Row-Level Security policies on documents, chunks, departments | Database engine blocks cross-tenant access |
| 7. Neo4j Graph | `WHERE tenant_id` on every Cypher query | Graph-level tenant isolation |
| 8. Foreign Keys | `ON DELETE CASCADE` from tenant to all child tables | Referential integrity enforcement |

## Technology Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| Framework | FastAPI 0.115+ | Async web framework with OpenAPI docs |
| Database | PostgreSQL 15 + pgvector | Relational storage + vector search (HNSW) |
| Graph DB | Neo4j 5.x | Knowledge graph for entity relationships |
| ORM | SQLAlchemy 2.0 (async) | Async database operations with Mapped/mapped_column |
| Auth | python-jose + passlib (bcrypt) | JWT generation/validation + password hashing |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | 384-dimensional text embeddings |
| LLM | OpenAI (gpt-4o-mini) / Ollama (llama3.1) | Answer generation (configurable, with fallback) |
| Validation | Pydantic v2 | Request/response schema validation |
| Config | pydantic-settings | Environment-based configuration |
| MCP | FastMCP | Model Context Protocol server (10 tools) |
| Testing | pytest + pytest-asyncio + httpx | Unit + integration test framework |
| Linting | Ruff | Fast Python linter and formatter |

## Project Structure

```
proairag/
├── src/
│   ├── main.py                    # FastAPI app factory (create_app)
│   ├── config.py                  # Settings (pydantic-settings, env vars)
│   ├── mcp_server.py              # MCP server — 10 tools (788 lines)
│   │
│   ├── api/                       # REST API routes (5 routers)
│   │   ├── auth.py                #   POST /auth/login, POST /auth/register
│   │   ├── tenants.py             #   POST /tenants/, GET /tenants/{id}
│   │   ├── documents.py           #   POST /documents/
│   │   ├── rag.py                 #   POST /rag/query
│   │   └── departments.py         #   CRUD /departments/, user assignment
│   │
│   ├── middleware/
│   │   └── tenant.py              # TenantContextMiddleware + DI types (141 lines)
│   │
│   ├── models/                    # SQLAlchemy ORM (6 models)
│   │   ├── tenant.py              #   Tenant (id, name, api_key, is_active)
│   │   ├── document.py            #   Document (tenant_id, department_id, title, content)
│   │   ├── chunk.py               #   Chunk (tenant_id, document_id, embedding[384])
│   │   ├── department.py          #   Department (tenant_id, name, description)
│   │   ├── user.py                #   User (tenant_id, email, password_hash, is_tenant_admin)
│   │   └── user_department.py     #   UserDepartment (user_id, department_id, role)
│   │
│   ├── schemas/                   # Pydantic v2 schemas (5 modules)
│   │   ├── tenant.py              #   TenantCreate, TenantResponse, TenantUpdate
│   │   ├── document.py            #   DocumentCreate, DocumentResponse
│   │   ├── rag.py                 #   RAGQuery, RAGResponse, RAGSource
│   │   ├── auth.py                #   UserCreate, UserResponse, LoginRequest, TokenResponse
│   │   └── department.py          #   DepartmentCreate/Response/Update, UserDepartment*
│   │
│   ├── services/                  # Business logic (9 services)
│   │   ├── tenant_service.py      #   Tenant CRUD + admin creation + default department
│   │   ├── auth_service.py        #   Password hashing, JWT tokens, user auth
│   │   ├── department_service.py  #   Department CRUD, user assignment, membership queries
│   │   ├── embedding_service.py   #   Text embeddings (sentence-transformers or hash fallback)
│   │   ├── ingestion_service.py   #   Document ingestion (chunking + embedding + storage)
│   │   ├── vector_service.py      #   pgvector similarity search (tenant + dept isolated)
│   │   ├── graph_service.py       #   Neo4j queries (entity context, summary, concepts)
│   │   ├── rag_service.py         #   Hybrid RAG orchestration (vector + graph + LLM)
│   │   └── llm_service.py         #   LLM provider interface (OpenAI, Local/Ollama)
│   │
│   ├── graph/                     # Neo4j integration (3 modules)
│   │   ├── neo4j_client.py        #   Async driver with execute/execute_write (singleton)
│   │   ├── entity_extractor.py    #   Regex-based NER (EMAIL, PHONE, DATE, URL, MONEY, CONCEPT)
│   │   └── graph_sync.py          #   Sync pipeline (MERGE nodes, relationships, co-occurrence)
│   │
│   └── db/
│       └── session.py             # Async engine, session factory, get_db() dependency
│
├── migrations/
│   ├── sql/                       # PostgreSQL migrations (6 files)
│   │   ├── 001_create_tenants.sql         # Tenants table + indexes
│   │   ├── 002_create_documents.sql       # Documents table + FK cascade
│   │   ├── 003_create_chunks.sql          # Chunks table + vector(384) + HNSW index
│   │   ├── 004_create_departments_users.sql # Departments, Users, User_Departments + dept on docs
│   │   ├── 005_rls_policies.sql           # RLS: documents + chunks (tenant isolation)
│   │   └── 006_rls_departments.sql        # RLS: departments (tenant isolation)
│   │
│   └── cypher/                    # Neo4j schema (3 files)
│       ├── 001_constraints.cypher   # Unique constraints (Tenant, Document, Chunk, Entity)
│       ├── 002_indexes.cypher       # Composite indexes on Entity, Chunk, Document
│       └── 003_department.cypher    # Department node constraints + indexes
│
├── tests/                         # Test suite (141 tests)
│   ├── conftest.py                # Root: markers, auto-marking by path
│   ├── test_mcp_server.py         # MCP server mock data setup + verification
│   ├── unit/                      # Unit tests (103 tests, no DB)
│   │   ├── test_auth_service.py       # Password hashing (5), JWT (6), auth flow (4), CRUD (5)
│   │   ├── test_department_service.py # CRUD (6), tenant isolation (4), assignments (5), queries (2)
│   │   ├── test_entity_extractor.py   # NER extraction (20)
│   │   ├── test_schemas.py            # Pydantic validation (42)
│   │   └── test_vector_service.py     # Embedding helpers (9)
│   └── integration/               # Integration tests (38 tests, Docker required)
│       ├── conftest.py                # Real DB fixtures (tenant, users, departments)
│       ├── test_full_api_flow.py      # End-to-end API (23 tests)
│       ├── test_auth.py               # Auth endpoints (8 tests)
│       ├── test_tenant_isolation.py   # Cross-tenant leakage prevention (5 tests)
│       └── test_department_isolation.py # Cross-department leakage prevention (3 tests)
│
├── MCP_SERVER.md                  # MCP server documentation (standalone)
├── pyproject.toml                 # Project metadata, dependencies, pytest/ruff config
└── README.md                      # This file
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker + Docker Compose (for PostgreSQL + Neo4j)
- Optional: OpenAI API key or Ollama instance for LLM answers

### 1. Install dependencies

```bash
# Core dependencies
pip install -e ".[dev]"

# Optional: real embeddings (~2GB with PyTorch)
pip install -e ".[embedding]"
```

### 2. Start infrastructure

```bash
docker compose up -d postgres neo4j
```

### 3. Configure environment

Set environment variables directly or create a `.env` file (see Environment Variables section):

```bash
export DATABASE_URL="postgresql+asyncpg://YOUR_USER:YOUR_PASS@localhost:5432/proairag"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="YOUR_NEO4J_PASSWORD"
export SECRET_KEY="YOUR_JWT_SECRET"
```

### 4. Run the application

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

Open the interactive API docs at http://localhost:8000/docs

## REST API Reference

All authenticated endpoints require either:
- `X-API-Key: sk-...` (tenant-level, admin access)
- `Authorization: Bearer <JWT>` (user-level, department-scoped)

### Health

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Health check |

### Tenants

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/tenants/` | None | Create tenant (returns api_key + admin user) |
| GET | `/tenants/{tenant_id}` | API Key | Get tenant by ID |

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/login` | None | Login with email + password, returns JWT |
| POST | `/auth/register` | API Key | Register new user in tenant |

### Documents

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/documents/` | API Key / JWT | Ingest document (chunking + embedding + storage) |

### RAG Query

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/rag/query` | API Key / JWT | Hybrid RAG query (vector + graph + LLM) |

### Departments

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/departments/` | API Key / JWT | List departments for tenant |
| POST | `/departments/` | API Key / JWT | Create department |
| GET | `/departments/{id}` | API Key / JWT | Get department |
| PUT | `/departments/{id}` | API Key / JWT | Update department |
| DELETE | `/departments/{id}` | API Key / JWT | Delete department |
| POST | `/departments/{id}/users` | JWT (admin only) | Assign user to department |
| DELETE | `/departments/{id}/users/{user_id}` | JWT (admin) | Remove user from department |

## API Examples

### Create a tenant with admin user

```bash
curl -X POST http://localhost:8000/tenants/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "admin_email": "admin@acme.com",
    "admin_password": "secure123",
    "admin_full_name": "Admin User"
  }'
# Response: {"id": "uuid", "name": "Acme Corp", "api_key": "sk-...", "is_active": true, ...}
```

### Login and get JWT

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@acme.com", "password": "secure123"}'
# Response: {"access_token": "eyJ...", "token_type": "bearer", "user": {...}}
```

### Create a department

```bash
curl -X POST http://localhost:8000/departments/ \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{"name": "Engineering", "description": "Software development team"}'
```

### Ingest a document

```bash
curl -X POST http://localhost:8000/documents/ \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Employee Handbook",
    "content": "The company provides 25 days of paid vacation per year...",
    "source": "hr/handbook.pdf",
    "content_type": "text"
  }'
```

### Query with RAG

```bash
curl -X POST http://localhost:8000/rag/query \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How many vacation days do employees get?",
    "top_k": 5,
    "include_graph_context": true,
    "graph_depth": 2
  }'
```

### Query with JWT (department-scoped)

```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the company policy?", "top_k": 5}'
```

## Hybrid RAG Pipeline

```
USER QUERY
    │
    ▼
┌─────────────────────────────┐
│  1. Embed query text        │  → 384-dim vector
│     (sentence-transformers) │     (or hash fallback)
└──────────┬──────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐  ┌──────────────────────────┐
│ 2a.      │  │ 2b. Entity extraction    │
│ Vector   │  │     + Graph traversal    │
│ Search   │  │                          │
│ (pgvec)  │  │ - Regex NER (6 types)   │
│ HNSW     │  │ - Neo4j path queries     │
│ cosine   │  │ - Co-occurrence edges    │
└────┬─────┘  └──────────┬───────────────┘
     │                    │
     ▼                    ▼
┌─────────────────────────────────────────┐
│ 3. Fuse context                         │
│     ┌────────────────────────────────┐  │
│     │ === DOCUMENT CONTEXT ===       │  │
│     │ [Doc 1: Handbook (0.892)]      │  │
│     │ The company provides 25 days... │  │
│     │                                │  │
│     │ === KNOWLEDGE GRAPH CONTEXT ===│  │
│     │ Entity: Company (CONCEPT)      │  │
│     │  -> Policy (CONCEPT) [2 hops]  │  │
│     └────────────────────────────────┘  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 4. LLM generation           │
│    OpenAI / Ollama / Fallback│
└────────────┬────────────────┘
             │
             ▼
    {"answer": "...", "sources": [...], "graph_context": [...]}
```

## Knowledge Graph Schema

```
(Tenant) ───[:OWNS]─────────> (Document) ───[:HAS_CHUNK]──> (Chunk)
   │                                   │                       │
   │                                  [:BELONGS_TO]             │
   │                                   │                      [:MENTIONS]
   │                                   ▼                       │
   │                            (Department)                    │
   │                              ▲    │                        │
   │                              │    │                        ▼
   │                        [:IN_TENANT]                    (Entity)
   │                              │               │
   │                              └───────────────┘
   │                                    │
   └────────────────────────────────────┘
                                          │
                                    [:CO_OCCURS_WITH]
                                          │
                                      (Entity)
```

### Entity Types (extracted via regex)

| Type | Pattern | Example |
|------|---------|---------|
| EMAIL | `user@domain.com` | `contact@acme.com` |
| PHONE | E.164 format | `+33612345678` |
| DATE | DD/MM/YYYY or Month DD, YYYY | `01/06/2025`, `June 1, 2025` |
| URL | `https://...` | `https://docs.acme.com` |
| MONEY | `$X,XXX.XX` | `$50,000.00` |
| CONCEPT | Proper nouns + acronyms | `Acme Corp`, `HR`, `GDPR` |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(required)* | PostgreSQL connection string |
| `NEO4J_URI` | *(required)* | Neo4j bolt URI |
| `NEO4J_USER` | *(required)* | Neo4j username |
| `NEO4J_PASSWORD` | *(required)* | Neo4j password |
| `SECRET_KEY` | *(required)* | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRE_HOURS` | `24` | Token expiration time |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model name |
| `EMBEDDING_DIMENSION` | `384` | Embedding vector dimension |
| `CHUNK_SIZE` | `512` | Document chunk size (words) |
| `CHUNK_OVERLAP` | `64` | Chunk overlap (words) |
| `TOP_K` | `5` | Default number of vector results |
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server bind port |
| `OPENAI_API_KEY` | (empty) | OpenAI API key for LLM |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama base URL (fallback) |
| `OLLAMA_MODEL` | `llama3.1` | Ollama model name |

## MCP Server

ProAiRag ships with a FastMCP server exposing 10 tools for AI assistant integrations.
See `MCP_SERVER.md` for complete documentation.

### Quick start

```bash
export API_KEY="sk-..."
fastmcp run src/mcp_server.py:mcp
```

### Available tools

| Tool | Description |
|------|-------------|
| `health_check()` | Server status and connection configuration |
| `list_tenants()` | All tenants (id, name, active status) |
| `create_tenant(name, ...)` | Create tenant with optional admin user |
| `list_documents(tenant_id?, department_id?, limit)` | Documents for a tenant |
| `ingest_document(title, content, tenant_id?, ...)` | Full ingestion pipeline |
| `rag_query(query, tenant_id?, top_k, include_graph, graph_depth)` | Hybrid RAG query |
| `graph_entity_context(entity_names, tenant_id?, depth)` | Entity relationships in graph |
| `graph_summary(tenant_id?, top_entities)` | Top connected entities |
| `find_related_concepts(concept, tenant_id?)` | Related CONCEPT entities |
| `list_departments(tenant_id?)` | Departments for a tenant |

### Installing into MCP clients

```bash
# Claude Code
fastmcp install claude-code src/mcp_server.py

# Cursor
fastmcp install cursor src/mcp_server.py

# Claude Desktop
fastmcp install claude-desktop src/mcp_server.py

# HTTP transport (any MCP client)
fastmcp run src/mcp_server.py:mcp --transport http --host 127.0.0.1 --port 9000
```

## Testing

### Run all tests

```bash
# Requires Docker (PostgreSQL + Neo4j running)
pytest

# Unit tests only (no DB needed)
pytest -m unit

# Integration tests only (Docker required)
pytest -m integration
```

### Test coverage

| Category | Count | Description |
|----------|-------|-------------|
| **Total** | **141** | All tests |
| Unit | 103 | Mocks, no database required |
| Integration | 38 | Real Docker database |
| └ Security (tenant) | 5 | Cross-tenant isolation |
| └ Security (department) | 3 | Cross-department isolation |
| └ API flow | 23 | End-to-end workflow |
| └ Auth | 8 | Login, JWT, endpoints |

### Test fixtures

Integration tests provide pre-built fixtures:
- `tenant_data`: Tenant with 2 departments (RH, Compta) and 2 users
- `hr_token` / `compta_token`: JWT tokens for each department user
- `tenant_a` / `tenant_b`: Isolated tenants for cross-tenant tests
- `cleanup_before_test`: Auto-cleanup between tests (autouse)

## Database Migrations

### SQL migrations (PostgreSQL)

Run in numeric order:

```bash
psql -U postgres -d proairag -f migrations/sql/001_create_tenants.sql
psql -U postgres -d proairag -f migrations/sql/002_create_documents.sql
psql -U postgres -d proairag -f migrations/sql/003_create_chunks.sql
psql -U postgres -d proairag -f migrations/sql/004_create_departments_users.sql
psql -U postgres -d proairag -f migrations/sql/005_rls_policies.sql
psql -U postgres -d proairag -f migrations/sql/006_rls_departments.sql
```

### Cypher migrations (Neo4j)

```bash
# Via Neo4j browser or cypher-shell
# migrations/cypher/001_constraints.cypher
# migrations/cypher/002_indexes.cypher
# migrations/cypher/003_department.cypher
```

## Department Access Control Flow

```
User logs in → JWT with (user_id, tenant_id, is_tenant_admin)
    │
    ▼
Request hits TenantContextMiddleware
    │
    ├── Extracts JWT → injects user_id, is_tenant_admin, tenant_id
    │
    ▼
RAG query service receives request
    │
    ├── is_tenant_admin = true?
    │     ├── YES → skip department filter (admin sees all)
    │     └── NO  → resolve user departments from user_departments table
    │
    ▼
Vector search with department filter:
    │
    ├── WHERE tenant_id = $tenant_id
    │   AND (d.department_id IS NULL
    │        OR d.department_id = ANY($department_ids))
    │
    ▼
Results returned (only from user's departments)
```

## Code Statistics

| Metric | Count |
|--------|-------|
| Python source files | 56 |
| Lines of code | ~5,664 |
| SQLAlchemy models | 6 |
| Service classes | 9 |
| API routes | 14 |
| Pydantic schemas | 14 |
| MCP tools | 10 |
| SQL migrations | 6 |
| Cypher migrations | 3 |
| Test files | 10 |
| Total tests | 141 |

## License

This project is part of ProAiRag — a hybrid multi-tenant RAG system.
