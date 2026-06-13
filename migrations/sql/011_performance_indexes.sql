-- Migration 011: Composite indexes for frequent query patterns

-- Composite index for chunk->document joins with tenant filtering
CREATE INDEX IF NOT EXISTS idx_chunks_tenant_doc ON chunks(tenant_id, document_id);

-- Composite index for conversation history (recent messages lookup)
CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conversation_id, created_at DESC);

-- Partial index for processed documents (most queries filter is_processed = true)
CREATE INDEX IF NOT EXISTS idx_docs_processed ON documents(tenant_id, department_id) WHERE is_processed = true;

-- Composite index for user_department lookups
CREATE INDEX IF NOT EXISTS idx_user_dept_user ON user_departments(user_id, department_id);
