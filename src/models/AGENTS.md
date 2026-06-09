# src/models/

## Purpose

SQLAlchemy ORM models defining the database schema for ProAirAg. Models enforce tenant isolation through foreign keys and cascade delete rules.

## Ownership

Owns all database table definitions. Depends on src/db/session.py for the Base class and engine.

## Local Contracts

- All models inherit from Base (DeclarativeBase in src/db/session.py)
- Every model with tenant data includes tenant_id as UUID foreign key
- Foreign keys use ondelete="CASCADE" for referential integrity
- UUIDs are primary keys with default=uuid.uuid4
- Use SQLAlchemy 2.0 Mapped/mapped_column syntax
- Relationships use lazy="selectin" to avoid N+1 queries

## Model Index

- tenant.py — Tenant: id, name, api_key, is_active, created_at (+ departments, users relationships)
- document.py — Document: tenant_id, department_id, title, content, source, content_type, is_processed
- chunk.py — Chunk: tenant_id, document_id, content, embedding (vector), chunk_index
- department.py — Department: tenant_id, name, description, created_at
- user.py — User: tenant_id, email, password_hash, full_name, is_tenant_admin, is_active
- user_department.py — UserDepartment: user_id, department_id, role (junction table)

## Work Guidance

- Do not add logic to models — keep them as pure data definitions
- New models must include tenant_id if they hold tenant data
- Use pgvector.sqlalchemy.Vector for embedding columns

## Verification

- py_compile on all model files
- RLS policies in migrations ensure tenant isolation at DB level

## Child DOX Index

No child DOX files yet.
