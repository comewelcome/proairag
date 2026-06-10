from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # PostgreSQL (required — no default)
    database_url: str = ""

    # Neo4j (required — no default)
    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # API
    secret_key: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5

    # LLM (OpenAI-compatible API on localhost:1234)
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_api_base: str = "http://localhost:1234/v1"
    openai_model: str = "gpt-4o-mini"

    # Ollama fallback
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    class Config:
        env_file = ".env"

    def __init__(self, **data):
        super().__init__(**data)
        required = ["database_url", "neo4j_uri", "neo4j_user", "neo4j_password", "secret_key"]
        missing = [k for k in required if not getattr(self, k)]
        if missing:
            raise ValueError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Set them in your .env file or environment."
            )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
