# src/services/

## Purpose

Business logic layer for ProAiRag. Implements core workflows: tenant management, document ingestion, embeddings, vector search, graph queries, RAG orchestration, and LLM integration.

## Ownership

Owns all business logic. Depends on models for data access, schemas for validation, and graph module for Neo4j operations.

## Local Contracts

- Each service is a class with factory function (e.g., get_rag_service)
- Services receive db session via constructor
- tenant_id MUST be explicitly passed to all service methods that access tenant data
- Embedding service uses singleton pattern (get_embedding_service)
- Neo4j client uses singleton pattern (get_neo4j_client)
- RAG service orchestrates: vector search + graph context + LLM generation
- LLM service provides abstract provider interface (OpenAI, Local)

## Service Index

- tenant_service.py — Tenant CRUD (create, get, update, deactivate) + admin user creation
- embedding_service.py — Text embeddings (sentence-transformers or hash fallback)
- ingestion_service.py — Document ingestion (chunking + embedding + storage) + department_id
- vector_service.py — pgvector similarity search (tenant + department isolated)
- graph_service.py — Neo4j graph queries (entity context, graph summary, concept lookup)
- rag_service.py — Hybrid RAG orchestration (vector + graph + LLM) + department filtering
- llm_service.py — LLM provider interface (OpenAI, Local/Ollama)
- auth_service.py — JWT auth: password hashing, token generation/validation, user registration
- department_service.py — Department CRUD, user assignment, department membership queries

## Work Guidance

- Services should be unit-testable (inject dependencies)
- Keep services focused on one responsibility
- Graph sync runs after document ingestion in ingestion pipeline

## Verification

- Unit tests for each service
- Integration tests for RAG pipeline

## Child DOX Index

No child DOX files yet.
