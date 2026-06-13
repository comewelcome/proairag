# src/middleware/

## Purpose

Request middleware for FastAPI. Handles dual authentication (JWT + API key), tenant context extraction, user context injection, and department access control before requests reach routes.

## Ownership

Owns request pre-processing, authentication, and context injection. Depends on Tenant and User models for validation.

## Local Contracts

- TenantContextMiddleware runs on every request
- Public paths (/health, /docs, /openapi.json, /redoc) bypass authentication
- Public API endpoints: POST /api/tenants/, POST /api/auth/login, GET /api/tenants/
- Frontend SPA routes (/, /login, /services, /documents, /chat, /settings, /admin/tenants, /admin/users, /admin/documents) bypass auth middleware
- Frontend static files (/assets/*, /index.html, /favicon.ico, /vite.svg) bypass auth middleware
- Dual auth: Authorization: Bearer JWT (user-level) or X-API-Key (tenant-level)
- JWT auth injects: user_id, user, is_tenant_admin, is_super_admin, auth_mode
- API key auth injects: tenant_id, tenant, auth_mode (no user context = admin-level access)
- Super admin bypass: is_super_admin=True skips tenant/department isolation checks
- Annotated types provide type-safe dependency injection

## Module Index

- tenant.py — TenantContextMiddleware, get_tenant_id, get_tenant, get_user_id, get_user, get_is_tenant_admin, get_is_super_admin, get_auth_mode, TenantId, TenantDep, UserId, UserDep, IsTenantAdmin, IsSuperAdmin, AuthMode

## Work Guidance

- Middleware should be fast — only validate API key, don't do heavy processing
- Invalid API key returns 403, missing key returns 401
- Tenant context is available in routes via Depends()

## Verification

- Tests verify 401/403 on invalid/missing API keys
- Tests verify tenant context injection

## Child DOX Index

No child DOX files yet.
