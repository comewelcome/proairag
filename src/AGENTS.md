# src/

## Purpose

Core application code for ProAirAg — a hybrid multi-tenant RAG system combining PostgreSQL vector search (tenant-isolated via Row-Level Security) with Neo4j knowledge graph reasoning.

## Ownership

Owns all Python source: FastAPI app, middleware, data models, schemas, services, graph operations, and API routes.

## Local Contracts

- All DB operations use async SQLAlchemy (SQLAlchemy 2.0 style with Mapped/mapped_column)
- Every model, service, and API route MUST scope by tenant_id
- tenant_id is injected via request.state by TenantContextMiddleware
- Use Pydantic v2 for all request/response schemas
- No direct DB queries in API routes — all logic flows through services
- Embedding service falls back to hash-based embedding when sentence-transformers is unavailable
- Neo4j queries always include WHERE tenant_id for isolation

## Work Guidance

- Service layer pattern: API route -> service -> DB/graph
- Services receive dependencies via factory functions (e.g., get_rag_service)
- Use dependency injection via FastAPI Depends for db sessions and tenant context
- Graph sync runs synchronously after document ingestion

## Verification

- py_compile on all .py files
- pytest with pytest-asyncio
- test_tenant_isolation.py for security verification

## Child DOX Index

- `src/api/AGENTS.md` — REST API routes: tenants, documents, RAG query
- `src/services/AGENTS.md` — Business logic: embedding, ingestion, RAG, vector, graph
- `src/models/AGENTS.md` — SQLAlchemy ORM models: Tenant, Document, Chunk
- `src/graph/AGENTS.md` — Neo4j integration: client, entity extraction, graph sync
- `src/middleware/AGENTS.md` — Request middleware: tenant context injection
- `src/schemas/AGENTS.md` — Pydantic schemas: request/response validation
- `src/db/AGENTS.md` — Database session management: async SQLAlchemy engine
