# src/api/

## Purpose

FastAPI route definitions for the ProAiRag REST API. Exposes tenant management, document ingestion, and RAG query endpoints.

## Ownership

Owns all HTTP routes and their request/response contracts. Depends on services for business logic and schemas for validation.

## Local Contracts

- All routes except /health and /tenants/* require X-API-Key header
- Tenant context is provided by TenantContextMiddleware (sets request.state.tenant_id)
- Use Annotated dependencies (TenantId, TenantDep) for type-safe injection
- Routes must not contain business logic — delegate to services
- Response models use Pydantic schemas from src/schemas/

## Endpoints

- POST /auth/login — Login with email + password, returns JWT token
- POST /auth/register — Register new user in tenant (returns JWT)
- POST /tenants/ — Create tenant (public, returns api_key + optional admin user)
- GET /tenants/{tenant_id} — Get tenant by ID
- POST /documents/ — Ingest document (tenant-isolated, optional department_id)
- POST /rag/query — Hybrid RAG query (vector + graph, tenant + department isolated)
- GET /departments/ — List departments for tenant
- POST /departments/ — Create department
- GET /departments/{id} — Get department
- PUT /departments/{id} — Update department
- DELETE /departments/{id} — Delete department
- POST /departments/{id}/users — Assign user to department (admin only)
- DELETE /departments/{id}/users/{user_id} — Remove user from department
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
