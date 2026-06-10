# src/

## Purpose

Core application code for ProAirAg — a hybrid multi-tenant RAG system with department-level access control, combining PostgreSQL vector search (tenant-isolated via Row-Level Security) with Neo4j knowledge graph reasoning.

## Ownership

Owns all Python source: FastAPI app, middleware, data models, schemas, services, graph operations, and API routes.

## Local Contracts

- All DB operations use async SQLAlchemy (SQLAlchemy 2.0 style with Mapped/mapped_column)
- Every model, service, and API route MUST scope by tenant_id
- Department-level filtering: users see only documents in their departments (tenant_admin bypasses)
- Dual authentication: JWT (user-level, department-scoped) + API key (tenant-level, admin access)
- tenant_id is injected via request.state by TenantContextMiddleware
- Use Pydantic v2 for all request/response schemas
- No direct DB queries in API routes — all logic flows through services
- Embedding service falls back to hash-based embedding when sentence-transformers is unavailable
- Neo4j queries always include WHERE tenant_id for isolation

## Work Guidance

- Service layer pattern: API route -> service -> DB/graph
- Services receive dependencies via factory functions (e.g., get_rag_service)
- Use dependency injection via FastAPI Depends for db sessions, tenant context, and user context
- Graph sync runs synchronously after document ingestion
- JWT tokens contain user_id, tenant_id, and is_tenant_admin claims

## Verification

- py_compile on all .py files
- pytest with pytest-asyncio
- Unit tests (mocks): `pytest tests/unit/`
- Integration tests (Docker): `pytest tests/integration/`
- Security tests verify tenant AND department isolation

## Child DOX Index

- `src/api/AGENTS.md` — REST API routes: tenants, documents, RAG, auth, departments
- `src/services/AGENTS.md` — Business logic: auth, department, embedding, ingestion, RAG, vector, graph
- `src/models/AGENTS.md` — SQLAlchemy ORM models: Tenant, Document, Chunk, Department, User, UserDepartment
- `src/graph/AGENTS.md` — Neo4j integration: client, entity extraction, graph sync (with Department nodes)
- `src/middleware/AGENTS.md` — Request middleware: JWT + API key auth, tenant/user context injection
- `src/schemas/AGENTS.md` — Pydantic schemas: request/response validation (auth, department, tenant, document, rag)
- `src/db/AGENTS.md` — Database session management: async SQLAlchemy engine
- `src/mcp_server.py` — MCP server: 10 tools exposing RAG, documents, graph, tenants via FastMCP
