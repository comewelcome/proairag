# migrations/

## Purpose

Database migration scripts for ProAiRag. Defines schema evolution for both PostgreSQL (SQL) and Neo4j (Cypher).

## Ownership

Owns all database schema definitions. Run during database initialization or migration.

## Local Contracts

- SQL migrations are run in numeric order (001, 002, ...)
- Cypher migrations are run in numeric order
-RLS policies have a NULL-safe fallback: when app.current_tenant_id is not set, rows are allowed (app-level WHERE clauses provide primary isolation). RLS acts as defense-in-depth.
- PostgreSQL uses pgvector extension for embeddings
- Neo4j uses constraints and indexes for performance

## Migration Index

SQL:
- 001_create_tenants.sql — Tenants table with UUID PK, unique constraints
- 002_create_documents.sql — Documents table with FK to tenants, cascade delete
- 003_create_chunks.sql — Chunks table with vector(384), hnsw index
- 004_create_departments_users.sql — Departments, Users, User_Departments tables + department_id on documents
- 005_rls_policies.sql — Row-Level Security policies for tenant isolation (documents, chunks)
- 006_rls_departments.sql — RLS policies for departments table
- 007_create_conversations.sql — Conversations + Messages tables for chat history (tenant-isolated)
- 008_create_tenant_settings.sql — Per-tenant RAG configuration (chunk_size, top_k, LLM provider, etc.)
- 009_add_llm_max_tokens.sql — Add llm_max_tokens column (default: 500) for LLM generation
- 010_add_super_admin.sql — Add is_super_admin boolean column to users table
- 011_performance_indexes.sql — Composite indexes: chunks(tenant_id, document_id), messages(conversation_id, created_at DESC), partial index on processed docs
- 012_rls_conversations_messages.sql — RLS policies for conversations and messages tables (defense-in-depth)

Cypher:
- 001_constraints.cypher — Unique constraints for Chunk, Entity (no Tenant/Document/Department nodes)
- 002_indexes.cypher — Composite indexes on Entity (type+tenant, name+tenant) and Chunk (tenant_id+document_id)
- 003_department.cypher — Department nodes removed; department_id is a Chunk property

## Work Guidance

- New migrations must use incremental numbering
- RLS policies should not be modified without security review
- Cypher migrations use MERGE for idempotency

## Verification

- Migrations run via docker-compose init scripts
- RLS policies verified by tenant isolation tests

## Child DOX Index

No child DOX files yet.
