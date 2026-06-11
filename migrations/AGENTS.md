# migrations/

## Purpose

Database migration scripts for ProAiRag. Defines schema evolution for both PostgreSQL (SQL) and Neo4j (Cypher).

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
- 004_create_departments_users.sql — Departments, Users, User_Departments tables + department_id on documents
- 005_rls_policies.sql — Row-Level Security policies for tenant isolation
- 006_rls_departments.sql — RLS policies for departments table
- 007_create_conversations.sql — Conversations + Messages tables for chat history (tenant-isolated)
- 008_create_tenant_settings.sql — Per-tenant RAG configuration (chunk_size, top_k, LLM provider, etc.)
- 009_add_llm_max_tokens.sql — Add llm_max_tokens column (default: 500) for LLM generation

Cypher:
- 001_constraints.cypher — Unique constraints for Tenant, Document, Chunk, Entity
- 002_indexes.cypher — Composite indexes on Entity, Chunk, Document by tenant_id
- 003_department.cypher — Department node constraints and indexes

## Work Guidance

- New migrations must use incremental numbering
- RLS policies should not be modified without security review
- Cypher migrations use MERGE for idempotency

## Verification

- Migrations run via docker-compose init scripts
- RLS policies verified by tenant isolation tests

## Child DOX Index

No child DOX files yet.
