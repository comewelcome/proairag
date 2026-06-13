# src/graph/

## Purpose

Neo4j knowledge graph integration for ProAiRag. Handles entity extraction, graph synchronization, and graph queries for semantic reasoning.

## Ownership

Owns all Neo4j interactions. Depends on Neo4j database and entity extraction results.

## Local Contracts

- Neo4j client uses singleton pattern (get_neo4j_client)
- Every Cypher query MUST include WHERE tenant_id for isolation
- Entity nodes carry tenant_id as a property
- Graph schema: Tenant -> owns -> Document -> has_chunk -> Chunk -> mentions -> Entity
- Graph schema: Tenant -> has_department -> Department -> contains -> Document -> belongs_to -> Department
- Entity relationships: CO_OCCURS_WITH between different entity types

## Module Index

- neo4j_client.py — Async Neo4j driver with execute/execute_write methods
- entity_extractor.py — NER: regex-based extraction (EMAIL, PHONE, DATE, URL, MONEY, CONCEPT) + concept extraction with noise word filtering
- graph_sync.py — Sync pipeline: merge nodes, create relationships, co-occurrence

## Work Guidance

- Use MERGE for idempotent node creation
- Always scope queries by tenant_id
- Entity extraction is synchronous; graph sync is async
- Entity IDs use uuid5(NAMESPACE_DNS, name) for determinism

## Verification

- Graph sync tests verify tenant isolation
- Cypher queries tested against Neo4j instance

## Child DOX Index

No child DOX files yet.
