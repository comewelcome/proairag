# src/api/

## Purpose

FastAPI route definitions for the ProAirAg REST API. Exposes tenant management, document ingestion, and RAG query endpoints.

## Ownership

Owns all HTTP routes and their request/response contracts. Depends on services for business logic and schemas for validation.

## Local Contracts

- All routes except /health and /tenants/* require X-API-Key header
- Tenant context is provided by TenantContextMiddleware (sets request.state.tenant_id)
- Use Annotated dependencies (TenantId, TenantDep) for type-safe injection
- Routes must not contain business logic — delegate to services
- Response models use Pydantic schemas from src/schemas/

## Endpoints

- POST /tenants/ — Create tenant (public, returns api_key)
- GET /tenants/{tenant_id} — Get tenant by ID
- POST /documents/ — Ingest document (tenant-isolated)
- POST /rag/query — Hybrid RAG query (vector + graph, tenant-isolated)
- GET /health — Health check (no auth required)

## Work Guidance

- Keep route handlers thin — they should only validate input and call services
- Error handling: HTTPException with appropriate status codes
- Use response_model for type-safe responses

## Verification

- API tests in tests/test_api/
- httpx AsyncClient for integration tests

## Child DOX Index

No child DOX files yet.
