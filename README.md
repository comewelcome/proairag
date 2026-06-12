# ProAiRag — Hybrid Multi-Tenant RAG Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Enterprise-grade **Retrieval-Augmented Generation** platform with strict multi-tenant isolation, department-level access control, and a knowledge graph reasoning layer. Ships with a full-featured React dashboard and an MCP server for AI agent integration.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [MCP Server](#mcp-server)
- [Dashboard](#dashboard)
- [Database Schema](#database-schema)
- [Security Model](#security-model)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)

---

## Overview

ProAiRag combines **vector similarity search** (PostgreSQL + pgvector HNSW) with **knowledge graph reasoning** (Neo4j) to deliver accurate, source-cited answers over your document corpus. Every query is scoped to a tenant and optionally filtered by department, enforcing strict data isolation at application, database, and graph levels.

```
User Query
   │
   ├──► Vector Search (pgvector HNSW) ──► Top-K relevant chunks
   │
   ├──► Entity Extraction ──► Graph Traversal (Neo4j) ──► Related entities
   │
   └──► Prompt Assembly ──► LLM (OpenAI-compatible / Ollama) ──► Answer + Sources
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Docker Compose                                  │
│                                                                         │
│  ┌──────────┐      ┌────────────────────────────────────────────────┐  │
│  │  Nginx   │─────►│              FastAPI (port 8000)               │  │
│  │  :80     │      │  ┌─────────────┐  ┌──────────────────────────┐ │  │
│  │          │      │  │   Frontend   │  │   /api/* (REST)          │ │  │
│  │          │      │  │   (SPA)      │  │   7 routers · 20+ routes │ │  │
│  │          │      │  └─────────────┘  └──────────┬───────────────┘ │  │
│  └──────────┘      └──────────────────┬───────────┼─────────────────┘  │
│                                      │           │                    │
│                       ┌──────────────┴──┐  ┌─────┴──────────┐         │
│                       │   PostgreSQL    │  │     Neo4j      │         │
│                       │   + pgvector    │  │   :7687 (bolt) │         │
│                       │   :5432         │  │   :7474 (web)  │         │
│                       └─────────────────┘  └────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Roles

| Service | Port | Purpose |
|---------|------|---------|
| **Nginx** | 80 | Reverse proxy, SPA routing, static file serving |
| **FastAPI** | 8000 | REST API + bundled React frontend serving |
| **PostgreSQL + pgvector** | 5432 | Relational data, document chunks, embeddings (HNSW index) |
| **Neo4j 5** | 7687/7474 | Knowledge graph (entities, relationships, concepts) |

---

## Features

### Core RAG Pipeline
- **Hybrid retrieval**: pgvector HNSW similarity search + Neo4j knowledge graph context
- **Document ingestion**: Automatic chunking, embedding, and graph entity extraction
- **Source citation**: Every answer includes ranked source documents with similarity scores
- **Graph reasoning**: Automatic entity extraction and relationship discovery for deeper context

### Multi-Tenant Isolation
- **Application-level**: JWT claims + middleware enforce tenant scoping on every request
- **Database-level**: PostgreSQL Row-Level Security (RLS) policies prevent cross-tenant queries
- **Graph-level**: All Cypher queries include `WHERE tenant_id = $tid` constraints
- **Department-level**: Users only access documents within their assigned departments

### Authentication
- **JWT tokens**: User-level auth with `tenant_id`, `user_id`, `is_tenant_admin` claims
- **API keys**: Tenant-level access for programmatic integration
- **Dual auth**: Routes accept either `Authorization: Bearer <JWT>` or `X-API-Key: <key>`

### Document Management
- **Supported formats**: PDF (via liteparse), TXT, DOCX, CSV
- **Upload**: Drag & drop interface, 50 MB max file size
- **Processing pipeline**: Parse → Chunk → Embed → Store → Graph sync
- **Filters**: By department, by name search

### Chat Interface
- **Persistent sessions**: Conversations stored with full message history
- **Session management**: Create, rename, delete conversations
- **RAG-powered**: Every assistant message includes retrieved sources and graph context
- **Department-scoped**: Chat queries respect user department membership

---

## Tech Stack

### Backend
| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115+ with uvicorn |
| ORM | SQLAlchemy 2.0 (async, `Mapped`/`mapped_column`) |
| Database | PostgreSQL 15 + pgvector extension |
| Graph DB | Neo4j 5 Community |
| Embeddings | sentence-transformers (MiniLM-L3-v2) or hash-based fallback |
| Auth | python-jose (JWT HS256), passlib (bcrypt) |
| Validation | Pydantic v2 |
| File parsing | liteparse (PDF), python-docx (DOCX) |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | React 19 + TypeScript (strict mode) |
| Build | Vite 7 + TailwindCSS v4 |
| Routing | TanStack Router |
| HTTP | Axios with JWT interceptor |
| UI | Lucide React icons, Sonner toasts, react-dropzone |
| Auth context | Custom `useAuth()` hook with localStorage persistence |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Orchestration | Docker Compose |
| Reverse proxy | Nginx Alpine |
| LLM | OpenAI-compatible API (llama.cpp) or Ollama |
| MCP | FastMCP (stdio + HTTP transport) |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose (v2.20+)
- Python 3.11+ (for local dev)
- Node.js 18+ (for frontend dev)
- Optional: llama.cpp server on `localhost:1234` for LLM responses

### Option A: Full Docker Stack (Recommended)

```bash
# 1. Clone and configure
git clone <repo-url> && cd proairag
cp .env.example .env
# Edit .env with your credentials (see Configuration section)

# 2. Build and start
docker compose up --build -d

# 3. Verify
curl http://localhost/health    # should return 200
# Dashboard: http://localhost
# API docs: http://localhost/docs
```

### Option B: Local Development

```bash
# 1. Start databases
docker compose up -d postgres neo4j

# 2. Install Python dependencies
pip install -e ".[dev]"
# Optional: install embedding models
pip install -e ".[embedding]"

# 3. Configure environment
cp .env.example .env
# Edit .env (use localhost for DB connections, not Docker service names)

# 4. Run backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 5. Run frontend (separate terminal)
cd frontend
npm install
npm run dev
# Dashboard: http://localhost:5173 (proxies API to :8000)
```

### Create Your First Tenant

```bash
curl -X POST http://localhost/api/tenants/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Company",
    "admin_email": "admin@company.com",
    "admin_password": "securepassword",
    "admin_full_name": "Admin User"
  }'
```

The response includes the tenant ID, API key, and a pre-created admin user.

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `NEO4J_URI` | Yes | — | Neo4j bolt URI (`bolt://localhost:7687`) |
| `NEO4J_USER` | Yes | — | Neo4j username |
| `NEO4J_PASSWORD` | Yes | — | Neo4j password |
| `SECRET_KEY` | Yes | — | JWT signing secret (use `python -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `LLM_PROVIDER` | No | `openai` | LLM provider: `openai`, `ollama`, or empty for fallback |
| `OPENAI_API_BASE` | No | `http://localhost:1234/v1` | OpenAI-compatible API endpoint |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model name for LLM generation |
| `OPENAI_API_KEY` | No | (empty) | API key (omit for local llama.cpp) |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama endpoint URL |
| `OLLAMA_MODEL` | No | `llama3.1` | Ollama model name |
| `LLM_MAX_TOKENS` | No | `500` | Max tokens for LLM responses |
| `EMBEDDING_MODEL` | No | `paraphrase-MiniLM-L3-v2` | Embedding model name |
| `CHUNK_SIZE` | No | `512` | Document chunk size (words) |
| `CHUNK_OVERLAP` | No | `64` | Chunk overlap (words) |
| `TOP_K` | No | `5` | Default number of vector search results |
| `JWT_EXPIRE_HOURS` | No | `24` | JWT token lifetime |

### LLM Setup

The platform supports three LLM modes:

**1. Local llama.cpp (recommended for privacy)**
```bash
# Start llama.cpp with OpenAI-compatible API
llama-server -m ./Qwen3.6-27B-UD-Q4_K_XL.gguf --host 0.0.0.0 --port 1234
# Configure:
LLM_PROVIDER=openai
OPENAI_API_BASE=http://host.docker.internal:1234/v1   # from Docker
# or
OPENAI_API_BASE=http://localhost:1234/v1              # from host
OPENAI_MODEL=Qwen3.6-27B-UD-Q4_K_XL.gguf
```

**2. Ollama**
```bash
ollama pull llama3.1
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

**3. OpenAI API**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

> **Note**: When running inside Docker, use `host.docker.internal` to reach the host machine. The `docker-compose.yml` includes `extra_hosts: ["host.docker.internal:host-gateway"]` for this purpose.

---

## API Reference

All endpoints are documented at `http://localhost/docs` (Swagger UI).

### Authentication

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/api/auth/login` | Public | Authenticate, returns JWT token |
| POST | `/api/auth/register` | Tenant-scoped | Register new user |

### Tenants

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/tenants/` | Public | List all active tenants |
| POST | `/api/tenants/` | Public | Create tenant + optional admin user |
| GET | `/api/tenants/{id}` | Auth | Get tenant details |

### Departments

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/departments/` | Auth | List tenant departments |
| POST | `/api/departments/` | Auth | Create department |
| GET | `/api/departments/{id}` | Auth | Get department |
| PUT | `/api/departments/{id}` | Auth | Update department |
| DELETE | `/api/departments/{id}` | Auth | Delete department |
| POST | `/api/departments/{id}/users` | Admin | Assign user to department |
| DELETE | `/api/departments/{id}/users/{uid}` | Admin | Remove user from department |

### Documents

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/documents/` | Auth | List documents (with department filter) |
| POST | `/api/documents/upload` | Auth | Upload file (multipart, PDF/TXT/DOCX/CSV) |
| DELETE | `/api/documents/{id}` | Auth | Delete document and all chunks |

### RAG

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/api/rag/query` | Auth | Hybrid RAG query (vector + graph + LLM) |

Request body:
```json
{
  "query": "What is our vacation policy?",
  "top_k": 5,
  "include_graph_context": true,
  "graph_depth": 2
}
```

### Chat

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/chat/sessions/` | Auth | List conversation sessions |
| POST | `/api/chat/sessions/` | Auth | Create new session |
| GET | `/api/chat/sessions/{id}` | Auth | Get session + messages |
| POST | `/api/chat/sessions/{id}/send` | Auth | Send message, get RAG response |
| PUT | `/api/chat/sessions/{id}/title` | Auth | Rename session |
| DELETE | `/api/chat/sessions/{id}` | Auth | Delete session |

### Settings

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/settings/` | Auth | Get tenant RAG settings |
| PUT | `/api/settings/` | Auth | Update tenant settings |
| GET | `/api/settings/stats` | Auth | System stats (documents, chunks, entities) |

---

## MCP Server

ProAiRag ships with a **Model Context Protocol** server for AI agent integration (Claude Code, Cursor, etc.).

```bash
# Run MCP server
python src/mcp_server.py

# Or with FastMCP CLI
fastmcp run src/mcp_server.py:mcp
```

### Available Tools

| Tool | Description |
|------|-------------|
| `health_check()` | Server status and connectivity |
| `list_tenants()` | Enumerate all tenants |
| `create_tenant(...)` | Create tenant with optional admin |
| `list_documents(...)` | List documents (tenant + department scoped) |
| `ingest_document(...)` | Ingest text content with chunking + embedding |
| `rag_query(...)` | Full hybrid RAG query |
| `graph_entity_context(...)` | Neo4j entity relationship lookup |
| `graph_summary(...)` | Top connected entities overview |
| `find_related_concepts(...)` | Concept relationship discovery |
| `list_departments(...)` | Department listing |

See [MCP_SERVER.md](MCP_SERVER.md) for full installation and usage guide.

---

## Dashboard

A React SPA served by the FastAPI backend at `http://localhost`.

### Pages

| Page | Route | Features |
|------|-------|----------|
| **Login** | `/login` | Email + password, JWT persistence |
| **Dashboard** | `/` | Stats overview, quick actions |
| **Services** | `/services` | Department CRUD (create, edit, delete) |
| **Documents** | `/documents` | Drag & drop upload, search, department filter |
| **Chat** | `/chat` | ChatGPT-style interface, sessions, source citations |
| **Settings** | `/settings` | Per-tenant RAG configuration |

### Frontend Development

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 with API proxy
npm run build        # Production build to dist/
```

---

## Database Schema

### PostgreSQL (9 migration files)

```
tenants
├── documents
│   ├── chunks (vector<384> + HNSW index)
│   └── department_id → departments
├── departments
│   └── user_departments → users
├── users
├── conversations
│   └── messages
└── tenant_settings
```

**Key design decisions**:
- All tables include `tenant_id` FK + RLS policies
- Chunks store 384-dimensional embeddings with HNSW index for fast ANN search
- RLS policies enforce tenant isolation at the database level
- Department filtering uses `user_departments` junction table

### Neo4j (3 migration files)

```
(Tenant) ←[:OWNS]← (Document) ←[:HAS_CHUNK]← (Chunk)
                                     │
                                  [:MENTIONS]
                                     │
                                 (Entity) ←[:RELATED_TO]← (Entity)
                                     │
                                  [:INSTANCE_OF]
                                     │
                                 (Concept)
```

---

## Security Model

### Defense-in-Depth

1. **Application layer**: Tenant context middleware injects `tenant_id` on every request. Department-level filtering in service layer.
2. **Database layer**: PostgreSQL RLS policies prevent any cross-tenant data access, even with direct DB connections.
3. **Graph layer**: All Cypher queries include `WHERE tenant_id = $tid` — no tenant data can leak through graph traversal.

### Authentication Flow

```
Login Request → Email + Password
                 │
                 ▼
            Verify against Users table
                 │
                 ▼
            Generate JWT with claims:
              - sub (user_id)
              - tenant_id
              - is_tenant_admin
              - exp / iat
                 │
                 ▼
            JWT stored in localStorage
            Axios interceptor attaches Bearer token to every request
```

### Secrets Management

- `.env` is gitignored; `.env.example` provides the template
- `config.py` raises `ValueError` if required secrets are missing
- No hardcoded credentials in source, tests, or Docker config
- Docker Compose uses `${VAR:-fallback}` syntax with non-credential defaults

---

## Development

### Project Structure

```
proairag/
├── src/
│   ├── main.py                  # FastAPI app entry, SPA serving, middleware
│   ├── config.py                # Pydantic Settings with validation
│   ├── api/                     # 7 route routers (auth, tenants, departments, ...)
│   ├── db/                      # Async SQLAlchemy engine and session factory
│   ├── graph/                   # Neo4j client, entity extractor, graph sync
│   ├── middleware/              # TenantContextMiddleware (JWT + API key auth)
│   ├── models/                  # 8 SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic v2 request/response schemas
│   ├── services/                # 11 business logic services
│   └── mcp_server.py            # FastMCP server (10 tools)
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # App entry + AuthProvider
│   │   ├── router.tsx           # TanStack Router (6 routes)
│   │   ├── pages/               # Login, Dashboard, Services, Documents, Chat, Settings
│   │   ├── components/          # Layout (Sidebar, Header) + common (Modal, Toast, ...)
│   │   ├── hooks/               # useAuth() context hook
│   │   ├── lib/                 # Axios API client with JWT interceptor
│   │   └── types/               # TypeScript interfaces
│   └── dist/                    # Vite build output (served by FastAPI)
├── migrations/
│   ├── sql/                     # 9 PostgreSQL migration scripts
│   └── cypher/                  # 3 Neo4j migration scripts
├── tests/                       # pytest (unit + integration)
├── Dockerfile                   # Backend image (Python 3.11, uvicorn)
├── docker-compose.yml           # Full stack (postgres, neo4j, api, nginx)
├── nginx.conf                   # Reverse proxy + SPA fallback routing
└── pyproject.toml               # Dependencies + tool config
```

### Code Conventions

- **Service layer pattern**: API routes → services → DB/graph (no business logic in routes)
- **Async throughout**: `async/await` for all DB operations, HTTP calls, and file I/O
- **Tenant scoping**: Every service method receives and validates `tenant_id`
- **Pydantic v2**: All request/response validation through schemas
- **Dependency injection**: FastAPI `Depends` for sessions, tenant context, user context

---

## Testing

```bash
# All tests
pytest

# Unit tests only (mocked DB)
pytest -m unit

# Integration tests (Docker databases)
pytest -m integration

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific file
pytest tests/test_mcp_server.py -v
```

---

## Deployment

### Production Checklist

- [ ] Generate a strong `SECRET_KEY` (not the default)
- [ ] Set real database passwords in `.env`
- [ ] Configure LLM provider with production endpoint
- [ ] Build frontend before Docker: `cd frontend && npm run build`
- [ ] Use persistent volumes for PostgreSQL and Neo4j data
- [ ] Set up TLS termination (Nginx or reverse proxy in front)
- [ ] Configure `JWT_EXPIRE_HOURS` appropriately for your use case
- [ ] Review and harden RLS policies before production use

### Production Docker

```bash
# Build frontend
cd frontend && npm run build && cd ..

# Start all services
docker compose --env-file .env up -d

# Check status
docker compose ps
docker compose logs -f api
```

---

## License

MIT
