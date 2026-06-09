-- ============================================================
-- ROW-LEVEL SECURITY: Isolation des departements
-- ============================================================

ALTER TABLE departments ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Politiques RLS: departments
-- ============================================================
CREATE POLICY tenant_department_isolation ON departments
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_department_insert ON departments
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_department_update ON departments
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_department_delete ON departments
    FOR DELETE
    USING (tenant_id = current_tenant_id());
