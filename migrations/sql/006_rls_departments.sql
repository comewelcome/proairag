-- ============================================================
-- ROW-LEVEL SECURITY: Isolation des departements
-- ============================================================

ALTER TABLE departments ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Politiques RLS: departments
-- ============================================================
CREATE POLICY tenant_department_isolation ON departments
    FOR SELECT
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_department_insert ON departments
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_department_update ON departments
    FOR UPDATE
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    )
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_department_delete ON departments
    FOR DELETE
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );
