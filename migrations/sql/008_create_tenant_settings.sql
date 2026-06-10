-- Migration 008: Create tenant_settings table
-- Per-tenant RAG configuration stored in PostgreSQL

CREATE TABLE IF NOT EXISTS tenant_settings (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    chunk_size INTEGER NOT NULL DEFAULT 512,
    chunk_overlap INTEGER NOT NULL DEFAULT 64,
    top_k INTEGER NOT NULL DEFAULT 5,
    embedding_model VARCHAR(256) NOT NULL DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    llm_provider VARCHAR(32) NOT NULL DEFAULT 'openai',
    llm_model VARCHAR(128) DEFAULT NULL,
    openai_api_key TEXT DEFAULT NULL,
    openai_api_base VARCHAR(256) DEFAULT NULL,
    ollama_base_url VARCHAR(256) DEFAULT NULL,
    ollama_model VARCHAR(128) DEFAULT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comment for documentation
COMMENT ON TABLE tenant_settings IS 'Per-tenant RAG and LLM configuration';
COMMENT ON COLUMN tenant_settings.llm_provider IS 'openai, ollama, or fallback';
