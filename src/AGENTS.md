# src/

## Purpose

Core application code for ProAiRag — a hybrid multi-tenant RAG system with department-level access control, combining PostgreSQL vector search (tenant-isolated via Row-Level Security) with Neo4j knowledge graph reasoning. Includes a React dashboard SPA served by FastAPI.

## Ownership

Owns all Python source: FastAPI app, middleware, data models, schemas, services, graph operations, and API routes. Serves the React SPA frontend (frontend/dist/).

## Local Contracts

- All DB operations use async SQLAlchemy (SQLAlchemy 2.0 style with Mapped/mapped_column)
- Every model, service, and API route MUST scope by tenant_id
- Department-level filtering: users see only documents in their departments (tenant_admin bypasses)
- Dual authentication: JWT (user-level, department-scoped) + API key (tenant-level, admin access)
- tenant_id is injected via request.state by TenantContextMiddleware
- Use Pydantic v2 for all request/response schemas
- No direct DB queries in API routes — all logic flows through services
- Embedding service uses sentence-transformers/paraphrase-MiniLM-L3-v2 by default, falls back to hash-based embedding when sentence-transformers is unavailable
- Neo4j queries always include WHERE tenant_id for isolation
- LLM defaults to OpenAI-compatible API on host.docker.internal:1234 (llama.cpp Qwen3.6-27B-UD-Q4_K_XL.gguf), configurable via LLM_PROVIDER env var, max 500 tokens, 300s timeout. Docker Compose sets extra_hosts for host.docker.internal resolution.
- FastAPI serves the React SPA frontend (frontend/dist/) with catchall routing
- TenantContextMiddleware excludes frontend routes (/assets/, /, /login, /services, /documents, /chat, /settings, /admin/tenants, /admin/users, /admin/documents) from auth
- **Security: `src/config.py` Settings raises `ValueError` if required secrets (database_url, neo4j_*, secret_key) are missing — never use default passwords**
- **Security: `src/mcp_server.py` raises `RuntimeError` at import time if DATABASE_URL or NEO4J_* env vars are unset**

## Work Guidance

- Service layer pattern: API route -> service -> DB/graph
- Services receive dependencies via factory functions (e.g., get_rag_service)
- Use dependency injection via FastAPI Depends for db sessions, tenant context, and user context
- Graph sync runs synchronously after document ingestion
- JWT tokens contain user_id, tenant_id, is_tenant_admin, and is_super_admin claims

## Verification

- py_compile on all .py files
- pytest with pytest-asyncio
- Unit tests (mocks): `pytest tests/unit/`
- Integration tests (Docker): `pytest tests/integration/`
- Security tests verify tenant AND department isolation

## Child DOX Index

- `src/api/AGENTS.md` — REST API routes: auth, tenants, departments, documents, rag, chat, settings, admin (super admin)
- `src/services/AGENTS.md` — Business logic: auth, department, embedding, ingestion, RAG, vector, graph, llm, chat, settings
- `src/models/AGENTS.md` — SQLAlchemy ORM models: Tenant, Document, Chunk, Department, User, UserDepartment, Conversation, Message, TenantSettings
- `src/graph/AGENTS.md` — Neo4j integration: client, entity extraction, graph sync (with Department nodes)
- `src/middleware/AGENTS.md` — Request middleware: JWT + API key auth, tenant/user context injection, frontend route exclusion
- `src/schemas/AGENTS.md` — Pydantic schemas: request/response validation (auth, department, tenant, document, rag, chat, settings)
- `src/db/AGENTS.md` — Database session management: async SQLAlchemy engine
- `src/mcp_server.py` — MCP server: 10 tools exposing RAG, documents, graph, tenants via FastMCP. Entity extraction uses shared EntityExtractor from entity_extractor.py. Standalone with its own DB engine and Neo4j driver.
