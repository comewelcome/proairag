// Constraints for the simplified Neo4j schema
// Neo4j stores ONLY Chunk references and Entity nodes with relationships.
// No Tenant/Document/Department nodes — tenant_id is a property on Chunk and Entity.

CREATE CONSTRAINT chunk_unique IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT entity_tenant_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE (e.id, e.tenant_id) IS UNIQUE;
