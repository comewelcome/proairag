# tests/

## Purpose

Test suite for ProAirAg. Verifies tenant isolation, department isolation (both security-critical), API behavior, and service functionality.

## Ownership

Owns all test code: fixtures, unit tests, integration tests. Depends on src/ for production code.

## Local Contracts

- pytest with pytest-asyncio for async test support
- httpx AsyncClient for API integration tests
- Unit tests use mocks (no DB required) — run with `pytest tests/unit/`
- Integration tests use real Docker database — run with `pytest tests/integration/`
- Security tests MUST verify tenant and department isolation — failure is a security breach
- Auto-marked: tests in tests/unit/ get `@pytest.mark.unit`, tests in tests/integration/ get `@pytest.mark.integration`
- All 141 tests pass with Docker (PostgreSQL + pgvector)
- Session-scoped fixtures for shared state across integration tests

## Test Structure

```
tests/
├── conftest.py              # Root conftest: markers, auto-marking by path
├── unit/                    # Unit tests (mocks, no DB)
│   ├── test_auth_service.py      # Password hashing, JWT, auth flow
│   ├── test_department_service.py # Department CRUD, user assignment
│   ├── test_entity_extractor.py   # NER extraction (regex)
│   ├── test_schemas.py            # Pydantic validation
│   └── test_vector_service.py     # Embedding helpers
├── integration/             # Integration tests (real Docker DB)
│   ├── conftest.py              # Real DB fixtures (tenant, users, departments)
│   ├── test_mcp_server.py       # MCP server mock data setup + verification
│   ├── test_full_api_flow.py    # End-to-end API tests (23 tests)
│   ├── test_auth.py             # Auth endpoints (8 tests)
│   ├── test_tenant_isolation.py # Tenant isolation (5 tests)
│   └── test_department_isolation.py # Department isolation (3 tests)
```

## Test Index

### Unit tests (103 tests, no DB)
- unit/test_auth_service.py — Password hashing (5), JWT tokens (6), auth flow (4), user CRUD (5)
- unit/test_department_service.py — CRUD (6), tenant isolation (4), assignments (5), queries (2)
- unit/test_entity_extractor.py — Email/phone/date/URL/money/concept extraction (20)
- unit/test_schemas.py — All Pydantic schemas validation (42)
- unit/test_vector_service.py — Embedding to SQL string conversion (9)

### Integration tests (38 tests, Docker required)
- integration/test_full_api_flow.py — Tenant creation, departments, auth, document isolation, cross-tenant isolation (23 tests)
- integration/test_auth.py — Login, JWT auth, department endpoints (8 tests)
- integration/test_tenant_isolation.py — Cross-tenant data leakage prevention (5 tests)
- integration/test_department_isolation.py — Cross-department data leakage prevention (3 tests)

## Work Guidance

- Security tests (tenant + department isolation) are critical — they must not be skipped
- Use fixtures for tenant/user/department setup, not inline creation
- Test both positive and negative cases for auth
- API tests verify HTTP status codes and response schemas
- Unit tests should be fast (< 10ms each)
- Integration tests are slower (DB I/O) — mark with `@pytest.mark.integration`
- Docker containers must be running: `docker compose up -d postgres neo4j`

## Child DOX Index

No child DOX files yet.
