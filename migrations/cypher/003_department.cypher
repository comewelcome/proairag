CREATE CONSTRAINT department_unique IF NOT EXISTS
FOR (d:Department) REQUIRE (d.id, d.tenant_id) IS UNIQUE;

CREATE INDEX department_tenant_idx IF NOT EXISTS
FOR (d:Department) ON (d.tenant_id, d.name);
