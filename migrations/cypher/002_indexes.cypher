// Indexes for fast lookups in the simplified Neo4j schema

// Entity lookups by tenant + type or tenant + name
CREATE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.type, e.tenant_id);

CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name, e.tenant_id);

// Chunk lookup by tenant + document (for delete_document cascade)
CREATE INDEX chunk_tenant_doc_idx IF NOT EXISTS
FOR (c:Chunk) ON (c.tenant_id, c.document_id);
