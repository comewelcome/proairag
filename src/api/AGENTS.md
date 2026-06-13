# src/api/

## Purpose

FastAPI route definitions for the ProAiRag REST API. Exposes tenant management, document ingestion, RAG queries, chat sessions, and settings endpoints. All routes are prefixed with /api/ for dashboard integration.

## Ownership

Owns all HTTP routes and their request/response contracts. Depends on services for business logic and schemas for validation.

## Local Contracts

- All routes under /api/* require JWT or API key authentication (except /health and public endpoints like POST /api/tenants/, POST /api/auth/login, GET /api/tenants/)
- Frontend routes (/login, /services, /documents, /chat, /settings, /assets/*) bypass auth middleware
- Tenant context is provided by TenantContextMiddleware (sets request.state.tenant_id)
- Use Annotated dependencies (TenantId, TenantDep) for type-safe injection
- Routes must not contain business logic — delegate to services
- Response models use Pydantic schemas from src/schemas/

## Endpoints

All API routes are prefixed with `/api/` for the dashboard frontend integration.

- POST /api/auth/login — Login with email + password, returns JWT token
- POST /api/auth/register — Register new user in tenant (returns JWT)
- GET /api/tenants/ — List all tenants (public, for dashboard)
- POST /api/tenants/ — Create tenant (public, returns api_key + optional admin user)
- GET /api/tenants/{tenant_id} — Get tenant by ID
- GET /api/departments/ — List departments for tenant
- POST /api/departments/ — Create department
- GET /api/departments/{id} — Get department
- PUT /api/departments/{id} — Update department
- DELETE /api/departments/{id} — Delete department
- POST /api/departments/{id}/users — Assign user to department (admin only)
- DELETE /api/departments/{id}/users/{user_id} — Remove user from department
- GET /api/documents/ — List documents (tenant-isolated, optional department filter)
- POST /api/documents/ — Ingest document from JSON payload (tenant-isolated, optional department_id)
- POST /api/documents/upload — Upload file (PDF/TXT/DOCX), parse with LiteParse, chunk, embed, store
- DELETE /api/documents/{doc_id} — Delete document and chunks
- POST /api/rag/query — Hybrid RAG query (vector + graph, tenant + department isolated)
- POST /api/chat/sessions/ — Create new chat session
- GET /api/chat/sessions/ — List chat sessions for tenant
- GET /api/chat/sessions/{session_id} — Get session messages
- POST /api/chat/sessions/{session_id}/send — Send message, get RAG response (user_id + is_tenant_admin scoped)
- PUT /api/chat/sessions/{session_id}/title — Rename session
- DELETE /api/chat/sessions/{session_id} — Delete session
- GET /api/settings/ — Get tenant RAG settings
- PUT /api/settings/ — Update tenant RAG settings
- GET /api/settings/stats — Get system stats (docs, chunks, entities, DB connectivity)
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
