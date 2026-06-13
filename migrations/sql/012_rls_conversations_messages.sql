-- Migration 012: Row-Level Security for conversations and messages
-- Defense-in-depth: tenant isolation at DB level for chat history

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Politiques RLS: conversations
-- ============================================================
CREATE POLICY tenant_conversation_select ON conversations
    FOR SELECT
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_conversation_insert ON conversations
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_conversation_update ON conversations
    FOR UPDATE
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    )
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

CREATE POLICY tenant_conversation_delete ON conversations
    FOR DELETE
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)::UUID
    );

-- ============================================================
-- Politiques RLS: messages
-- Messages are scoped to conversations, so we check the
-- conversation's tenant_id through a subquery.
-- ============================================================
CREATE POLICY tenant_message_select ON messages
    FOR SELECT
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR conversation_id IN (
            SELECT id FROM conversations
            WHERE tenant_id = current_setting('app.current_tenant_id', true)::UUID
        )
    );

CREATE POLICY tenant_message_insert ON messages
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR conversation_id IN (
            SELECT id FROM conversations
            WHERE tenant_id = current_setting('app.current_tenant_id', true)::UUID
        )
    );

CREATE POLICY tenant_message_delete ON messages
    FOR DELETE
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR conversation_id IN (
            SELECT id FROM conversations
            WHERE tenant_id = current_setting('app.current_tenant_id', true)::UUID
        )
    );
