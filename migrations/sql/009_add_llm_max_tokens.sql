-- Migration 009: Add llm_max_tokens to tenant_settings
-- Controls max output tokens for LLM generation (default: 500)

ALTER TABLE tenant_settings
    ADD COLUMN IF NOT EXISTS llm_max_tokens INTEGER NOT NULL DEFAULT 500;

COMMENT ON COLUMN tenant_settings.llm_max_tokens IS 'Maximum tokens for LLM generation';
