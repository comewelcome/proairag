# src/middleware/

## Purpose

Request middleware for FastAPI. Handles tenant context extraction, API key validation, and tenant resolution before requests reach routes.

## Ownership

Owns request pre-processing and tenant context injection. Depends on Tenant model for API key validation.

## Local Contracts

- TenantContextMiddleware runs on every request
- Public paths (/health, /docs, /openapi.json, /redoc) bypass tenant validation
- X-API-Key header is required for all authenticated routes
- Tenant context (tenant_id, tenant object) is stored on request.state
- Annotated types (TenantId, TenantDep) provide type-safe dependency injection

## Module Index

- tenant.py — TenantContextMiddleware, get_tenant_id, get_tenant, TenantId, TenantDep

## Work Guidance

- Middleware should be fast — only validate API key, don't do heavy processing
- Invalid API key returns 403, missing key returns 401
- Tenant context is available in routes via Depends()

## Verification

- Tests verify 401/403 on invalid/missing API keys
- Tests verify tenant context injection

## Child DOX Index

No child DOX files yet.
