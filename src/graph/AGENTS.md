# src/graph/

## Purpose

Neo4j knowledge graph integration for ProAiRag. Handles entity extraction, graph synchronization, and graph queries for semantic reasoning.

## Ownership

Owns all Neo4j interactions. Depends on Neo4j database and entity extraction results.

## Local Contracts

- Neo4j client uses singleton pattern (get_neo4j_client)
- Every Cypher query MUST include WHERE tenant_id for isolation
- Entity nodes carry tenant_id as a property
- **Neo4j stores ONLY Chunk references and Entity nodes with relationships — no content duplication**
- **PostgreSQL is the source of truth for Tenants, Documents, Departments, Users, Chunks, Conversations**
- Graph schema: `Chunk {id, tenant_id, document_id, department_id, chunk_index} --[:MENTIONS]--> Entity {id, tenant_id, name, type, confidence}`
- Entity relationships: `CO_OCCURS_WITH` between different entity types (with `count` weight)
- No Tenant/Document/Department nodes — those IDs are stored as Chunk properties
- Co-occurrence is limited to top 20 entities by confidence per document (avoids O(N^2) explosion)
- `delete_document()` removes orphaned Chunks and Entities when a document is deleted from PostgreSQL

## Module Index

- neo4j_client.py — Async Neo4j driver with execute/execute_write methods + initialize_schema
- entity_extractor.py — NER: regex-based extraction (EMAIL, PHONE, DATE, URL, MONEY, CONCEPT) + concept extraction with noise word filtering
- graph_sync.py — Sync pipeline: batch MERGE for Chunks (no content), Entities, MENTIONS relations, co-occurrence + delete_document for cascade cleanup

## Work Guidance

- Use MERGE for idempotent node creation
- Always scope queries by tenant_id
- Entity extraction is synchronous; graph sync is async
- Entity IDs use uuid5(NAMESPACE_DNS, name) for determinism
- Chunk nodes carry only reference properties (id, tenant_id, document_id, department_id, chunk_index) — NEVER store content text
- Use UNWIND for batch operations instead of per-entity round trips

## Verification

- Graph sync tests verify tenant isolation
- Cypher queries tested against Neo4j instance

## Child DOX Index

No child DOX files yet.
