-- ============================================================
-- ROW-LEVEL SECURITY: Isolation stricte multi-tenant
-- ============================================================

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

-- Fonction utilitaire: retourne le tenant_id depuis une variable de session
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS UUID AS $$
    SELECT current_setting('app.current_tenant_id', true)::UUID;
$$ LANGUAGE SQL STABLE;

-- Fonction pour les super-admins (bypass RLS)
CREATE OR REPLACE FUNCTION is_tenant_admin(tenant_id uuid)
RETURNS BOOLEAN AS $$
    SELECT
        current_setting('app.current_tenant_id', true)::UUID = tenant_id
        OR current_setting('app.is_admin', true)::BOOLEAN = true;
$$ LANGUAGE SQL STABLE;

-- ============================================================
-- Politiques RLS: documents
-- ============================================================
CREATE POLICY tenant_document_isolation ON documents
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_document_insert ON documents
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_document_update ON documents
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_document_delete ON documents
    FOR DELETE
    USING (tenant_id = current_tenant_id());

-- ============================================================
-- Politiques RLS: chunks
-- ============================================================
CREATE POLICY tenant_chunk_isolation ON chunks
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_chunk_insert ON chunks
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_chunk_update ON chunks
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_chunk_delete ON chunks
    FOR DELETE
    USING (tenant_id = current_tenant_id());
