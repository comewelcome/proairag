# migrations/

## Purpose

Database migration scripts for ProAirAg. Defines schema evolution for both PostgreSQL (SQL) and Neo4j (Cypher).

## Ownership

Owns all database schema definitions. Run during database initialization or migration.

## Local Contracts

- SQL migrations are run in numeric order (001, 002, ...)
- Cypher migrations are run in numeric order
- RLS policies are in a separate migration file (005) run after table creation
- PostgreSQL uses pgvector extension for embeddings
- Neo4j uses constraints and indexes for performance

## Migration Index

SQL:
- 001_create_tenants.sql — Tenants table with UUID PK, unique constraints
- 002_create_documents.sql — Documents table with FK to tenants, cascade delete
- 003_create_chunks.sql — Chunks table with vector(384), hnsw index
- 005_rls_policies.sql — Row-Level Security policies for tenant isolation

Cypher:
- 001_constraints.cypher — Unique constraints for Tenant, Document, Chunk, Entity
- 002_indexes.cypher — Composite indexes on Entity, Chunk, Document by tenant_id

## Work Guidance

- New migrations must use incremental numbering
- RLS policies should not be modified without security review
- Cypher migrations use MERGE for idempotency

## Verification

- Migrations run via docker-compose init scripts
- RLS policies verified by tenant isolation tests

## Child DOX Index

No child DOX files yet.
