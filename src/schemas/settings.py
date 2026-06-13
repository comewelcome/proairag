from pydantic import BaseModel, Field


class RagSettingsUpdate(BaseModel):
    chunk_size: int | None = Field(default=None, ge=64, le=2048)
    chunk_overlap: int | None = Field(default=None, ge=0, le=512)
    top_k: int | None = Field(default=None, ge=1, le=50)
    embedding_model: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    openai_api_key: str | None = None
    openai_api_base: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    llm_max_tokens: int | None = None


class RagSettingsResponse(BaseModel):
    chunk_size: int
    chunk_overlap: int
    top_k: int
    embedding_model: str
    llm_provider: str
    llm_model: str | None = None
    openai_api_key: str | None = None
    openai_api_base: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    llm_max_tokens: int = 500

    model_config = {"from_attributes": True}


class SystemStats(BaseModel):
    document_count: int
    chunk_count: int
    entity_count: int
    postgres_connected: bool
    neo4j_connected: bool
