# tests/

## Purpose

Test suite for ProAirAg. Verifies tenant isolation (security-critical), API behavior, and service functionality.

## Ownership

Owns all test code: fixtures, unit tests, integration tests. Depends on src/ for production code.

## Local Contracts

- pytest with pytest-asyncio for async test support
- httpx AsyncClient for API integration tests
- Fixtures in conftest.py (app, client, tenant_a, tenant_b, db_session)
- Security tests MUST verify tenant isolation — failure is a security breach

## Test Index

- conftest.py — Shared fixtures: app, client, tenants, db_session
- test_tenant_isolation.py — Security tests: tenant ID enforcement, API key auth

## Work Guidance

- Security tests (tenant isolation) are critical — they must not be skipped
- Use fixtures for tenant setup, not inline creation
- Test both positive and negative cases for auth
- API tests verify HTTP status codes and response schemas

## Verification

- pytest runs all tests
- test_tenant_isolation.py verifies no cross-tenant data access

## Child DOX Index

No child DOX files yet.
