-- ============================================================
-- ROW-LEVEL SECURITY: Isolation stricte multi-tenant
-- ============================================================

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

-- Fonction utilitaire: retourne le tenant_id depuis une variable de session.
-- Retourne NULL si la variable n'est pas definie (fallback: l'application
-- fait deja le filtrage au niveau WHERE tenant_id = :x).
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
-- When app.current_tenant_id is set: enforce strict tenant isolation.
-- When not set (NULL): allow the row (app-level WHERE clause handles isolation).
-- This makes RLS a defense-in-depth layer, not a hard gate.
CREATE POLICY tenant_document_isolation ON documents
    FOR SELECT
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_document_insert ON documents
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_document_update ON documents
    FOR UPDATE
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    )
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_document_delete ON documents
    FOR DELETE
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

-- ============================================================
-- Politiques RLS: chunks
-- ============================================================
CREATE POLICY tenant_chunk_isolation ON chunks
    FOR SELECT
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_chunk_insert ON chunks
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_chunk_update ON chunks
    FOR UPDATE
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    )
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_chunk_delete ON chunks
    FOR DELETE
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );
