CREATE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.type, e.tenant_id);

CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name, e.tenant_id);

CREATE INDEX chunk_tenant_idx IF NOT EXISTS
FOR (c:Chunk) ON (c.id, c.tenant_id);

CREATE INDEX document_tenant_idx IF NOT EXISTS
FOR (d:Document) ON (d.id, d.tenant_id);
